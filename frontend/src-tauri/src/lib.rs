use std::fmt::Write as _;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{Manager, RunEvent, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_START_TIMEOUT: Duration = Duration::from_secs(30);

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    api_base_url: String,
    session_token: String,
    native_updates: bool,
}

#[derive(Default)]
struct BackendState {
    child: Mutex<Option<CommandChild>>,
    connection: Mutex<Option<BackendConnection>>,
    startup_error: Mutex<Option<String>>,
}

impl BackendState {
    fn record_error(&self, message: String) {
        if let Ok(mut connection) = self.connection.lock() {
            *connection = None;
        }
        if let Ok(mut error) = self.startup_error.lock() {
            *error = Some(message);
        }
    }
}

#[tauri::command]
fn backend_connection(state: State<'_, BackendState>) -> Result<BackendConnection, String> {
    if let Ok(connection) = state.connection.lock() {
        if let Some(connection) = connection.as_ref() {
            return Ok(connection.clone());
        }
    }
    state
        .startup_error
        .lock()
        .ok()
        .and_then(|error| error.clone())
        .map_or_else(
            || Err("Локальный backend nfprogress ещё не готов.".to_string()),
            Err,
        )
}

fn reserve_loopback_port() -> Result<u16, String> {
    let listener = TcpListener::bind((BACKEND_HOST, 0))
        .map_err(|error| format!("Не удалось выбрать локальный порт: {error}"))?;
    listener
        .local_addr()
        .map(|address| address.port())
        .map_err(|error| format!("Не удалось определить локальный порт: {error}"))
}

fn create_session_token() -> Result<String, String> {
    let mut bytes = [0_u8; 32];
    getrandom::fill(&mut bytes)
        .map_err(|error| format!("Не удалось создать ключ локальной сессии: {error}"))?;
    let mut token = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(&mut token, "{byte:02x}").expect("writing to a String cannot fail");
    }
    Ok(token)
}

fn native_updates_enabled() -> bool {
    matches!(
        option_env!("NFPROGRESS_UPDATER_ENABLED"),
        Some("1") | Some("true")
    )
}

fn backend_is_healthy(port: u16) -> bool {
    let address = format!("{BACKEND_HOST}:{port}");
    let Ok(socket_address) = address.parse() else {
        return false;
    };
    let Ok(mut stream) = TcpStream::connect_timeout(&socket_address, Duration::from_millis(250))
    else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
    if stream
        .write_all(b"GET /health HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n")
        .is_err()
    {
        return false;
    }
    let mut response = [0_u8; 128];
    match stream.read(&mut response) {
        Ok(size) => {
            let status = &response[..size];
            status.starts_with(b"HTTP/1.1 200") || status.starts_with(b"HTTP/1.0 200")
        }
        Err(_) => false,
    }
}

fn wait_for_backend(port: u16) -> Result<(), String> {
    let deadline = Instant::now() + BACKEND_START_TIMEOUT;
    while Instant::now() < deadline {
        if backend_is_healthy(port) {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(100));
    }
    Err("Локальный backend nfprogress не ответил на /health за 30 секунд.".to_string())
}

fn stop_backend(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<BackendState>();
    if let Ok(mut child) = state.child.lock() {
        if let Some(child) = child.take() {
            let _ = child.kill();
        }
    };
}

pub fn run() {
    let app = tauri::Builder::default()
        .manage(BackendState::default())
        .plugin(tauri_plugin_single_instance::init(|app, _arguments, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .invoke_handler(tauri::generate_handler![backend_connection])
        .setup(|app| {
            let state = app.state::<BackendState>();
            let port = match reserve_loopback_port() {
                Ok(port) => port,
                Err(error) => {
                    state.record_error(error);
                    return Ok(());
                }
            };
            let token = match create_session_token() {
                Ok(token) => token,
                Err(error) => {
                    state.record_error(error);
                    return Ok(());
                }
            };

            let command = match app.shell().sidecar("nfprogress-backend") {
                Ok(command) => command,
                Err(error) => {
                    state.record_error(format!("Не удалось найти локальный backend: {error}"));
                    return Ok(());
                }
            };
            let mut arguments = vec![
                "--host".to_string(),
                BACKEND_HOST.to_string(),
                "--port".to_string(),
                port.to_string(),
                "--platform".to_string(),
                "desktop".to_string(),
                "--parent-pid".to_string(),
                std::process::id().to_string(),
                "--log-level".to_string(),
                "warning".to_string(),
            ];
            if cfg!(debug_assertions) {
                // Tauri dev must use the same synchronized test_data copy as
                // ``python main_UI.py``. Release bundles intentionally keep
                // their normal per-user app-data behavior.
                arguments.push("--dev-data".to_string());
            }
            let spawn_result = command
                .args(arguments)
                .env("NFPROGRESS_SESSION_TOKEN", &token)
                .env(
                    "NFPROGRESS_ALLOWED_ORIGINS",
                    "tauri://localhost,http://tauri.localhost,https://tauri.localhost,http://localhost:5173,http://127.0.0.1:5173",
                )
                .spawn();
            let (mut events, child) = match spawn_result {
                Ok(result) => result,
                Err(error) => {
                    state.record_error(format!("Не удалось запустить локальный backend: {error}"));
                    return Ok(());
                }
            };

            if let Err(error) = wait_for_backend(port) {
                let _ = child.kill();
                state.record_error(error);
                return Ok(());
            }

            if let Ok(mut connection) = state.connection.lock() {
                *connection = Some(BackendConnection {
                    api_base_url: format!("http://{BACKEND_HOST}:{port}"),
                    session_token: token,
                    native_updates: native_updates_enabled(),
                });
            }
            if let Ok(mut managed_child) = state.child.lock() {
                *managed_child = Some(child);
            }

            let app_handle = app.handle().clone();
            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    if let CommandEvent::Terminated(payload) = event {
                        let state = app_handle.state::<BackendState>();
                        state.record_error(format!(
                            "Локальный backend завершился (код: {:?}, сигнал: {:?}).",
                            payload.code, payload.signal
                        ));
                        break;
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build the nfprogress desktop application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_backend(app_handle);
        }
    });
}
