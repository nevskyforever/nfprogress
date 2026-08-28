use std::fmt::Write as _;
use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use serde::Serialize;
use tauri::{Manager, RunEvent, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_START_TIMEOUT: Duration = Duration::from_secs(30);
const UPDATE_MANIFEST_URL: &str = "https://nfproject.ru/app/update_manifest.json";
const UPDATE_MANIFEST_TIMEOUT: Duration = Duration::from_secs(10);

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    api_base_url: String,
    session_token: String,
    native_updates: bool,
    architecture: String,
    development: bool,
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

fn configure_rustls_provider() {
    // The updater plugin installs a provider in release builds. Tauri dev does
    // not load that plugin, so install ring here before reqwest creates TLS.
    let _ = rustls::crypto::ring::default_provider().install_default();
}

#[tauri::command]
async fn fetch_update_manifest() -> Result<serde_json::Value, String> {
    configure_rustls_provider();
    let client = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(5))
        .timeout(UPDATE_MANIFEST_TIMEOUT)
        .build()
        .map_err(|error| format!("Не удалось настроить проверку обновлений: {error}"))?;
    let response = client
        .get(UPDATE_MANIFEST_URL)
        .send()
        .await
        .map_err(|error| format!("Не удалось получить манифест обновления: {error}"))?
        .error_for_status()
        .map_err(|error| format!("Сервер обновлений вернул ошибку: {error}"))?;
    response
        .json::<serde_json::Value>()
        .await
        .map_err(|error| format!("Манифест обновления имеет неверный формат: {error}"))
}

#[cfg(test)]
mod tests {
    #[cfg(target_os = "macos")]
    use std::io::Write;
    use std::path::Path;
    #[cfg(target_os = "macos")]
    use std::process::{Command, Stdio};

    use super::{build_macos_updater_script, configure_rustls_provider, macos_update_target};

    #[test]
    fn update_client_has_a_rustls_crypto_provider() {
        configure_rustls_provider();
        assert!(reqwest::Client::builder().build().is_ok());
    }

    #[test]
    fn macos_updater_can_install_an_app_from_a_nested_dmg() {
        let script = build_macos_updater_script(
            "https://nfproject.ru/app/update.zip",
            Path::new("/Applications/nfprogress.app"),
            "aabbcc",
            42,
            Path::new("/tmp/nfprogress-update.log"),
            123,
        );

        assert!(script.contains("DMG_PATH=$(find"));
        assert!(script.contains("hdiutil attach \"$DMG_PATH\""));
        assert!(script.contains("find \"$MOUNT_POINT\""));
        assert!(script.contains("ditto \"$NEW_APP\" \"$TARGET_PATH\""));
    }

    #[cfg(debug_assertions)]
    #[test]
    fn tauri_dev_updates_the_installed_macos_app() {
        assert_eq!(
            macos_update_target(Path::new("/project/target/debug/nfprogress-desktop")),
            Some(Path::new("/Applications/nfprogress.app").to_path_buf()),
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn macos_updater_script_has_valid_shell_syntax() {
        let script = build_macos_updater_script(
            "https://nfproject.ru/app/update.zip",
            Path::new("/Applications/nfprogress.app"),
            "aabbcc",
            42,
            Path::new("/tmp/nfprogress-update.log"),
            123,
        );
        let mut child = Command::new("/bin/sh")
            .arg("-n")
            .stdin(Stdio::piped())
            .spawn()
            .expect("shell must start");
        child
            .stdin
            .take()
            .expect("shell stdin must be piped")
            .write_all(script.as_bytes())
            .expect("script must be written to shell");

        assert!(child.wait().expect("shell must finish").success());
    }
}

fn shell_literal(value: impl AsRef<str>) -> String {
    format!("'{}'", value.as_ref().replace('\'', "'\\''"))
}

fn macos_app_bundle(executable: &Path) -> Option<PathBuf> {
    executable
        .ancestors()
        .find(|path| path.extension().is_some_and(|extension| extension == "app"))
        .map(Path::to_path_buf)
}

fn macos_update_target(executable: &Path) -> Option<PathBuf> {
    macos_app_bundle(executable)
        .or_else(|| cfg!(debug_assertions).then(|| PathBuf::from("/Applications/nfprogress.app")))
}

fn build_macos_updater_script(
    download_url: &str,
    target: &Path,
    sha256: &str,
    size: u64,
    log_path: &Path,
    parent_pid: u32,
) -> String {
    let target_name = target.file_name().unwrap_or_default().to_string_lossy();
    format!(
        r#"#!/bin/sh
set -u
DOWNLOAD_URL={url}
SHA256={sha256}
SIZE={size}
TARGET_PATH={target}
TARGET_NAME={target_name}
PARENT_PID={pid}
LOG_PATH={log_path}
MOUNT_POINT=""

log() {{
    printf '%s %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >> "$LOG_PATH"
}}

fail() {{
    log "failed: $1"
    if [ -n "$MOUNT_POINT" ]; then
        hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
    fi
    osascript -e 'display alert "nfprogress" message "Не удалось установить обновление. Подробности: '"$LOG_PATH"'"' >/dev/null 2>&1 || true
    exit 1
}}

log "waiting for application process $PARENT_PID"
while kill -0 "$PARENT_PID" >/dev/null 2>&1; do sleep 1; done
sleep 1

WORK_DIR=$(mktemp -d "${{TMPDIR:-/tmp/}}nfprogress-update.XXXXXX") || fail "Не удалось создать временную папку."
ZIP_PATH="$WORK_DIR/update.zip"
EXTRACT_DIR="$WORK_DIR/extract"
mkdir -p "$EXTRACT_DIR" || fail "Не удалось создать папку распаковки."

log "downloading $DOWNLOAD_URL"
curl -fL --connect-timeout 20 --retry 2 -o "$ZIP_PATH" "$DOWNLOAD_URL" || fail "Не удалось скачать архив обновления."
[ "$(stat -f %z "$ZIP_PATH")" = "$SIZE" ] || fail "Размер архива обновления не совпадает с манифестом."
[ "$(shasum -a 256 "$ZIP_PATH" | awk '{{print $1}}')" = "$SHA256" ] || fail "Контрольная сумма архива обновления не совпадает с манифестом."
ditto -x -k "$ZIP_PATH" "$EXTRACT_DIR" || unzip -q "$ZIP_PATH" -d "$EXTRACT_DIR" || fail "Не удалось распаковать zip-архив."

NEW_APP=$(find "$EXTRACT_DIR" -maxdepth 4 -name "$TARGET_NAME" -type d -print -quit)
if [ -z "$NEW_APP" ]; then
    NEW_APP=$(find "$EXTRACT_DIR" -maxdepth 4 -name "*.app" -type d -print -quit)
fi

if [ -z "$NEW_APP" ]; then
    DMG_PATH=$(find "$EXTRACT_DIR" -maxdepth 4 -name "*.dmg" -type f -print -quit)
    if [ -n "$DMG_PATH" ]; then
        log "mounting $DMG_PATH"
        MOUNT_OUTPUT=$(hdiutil attach "$DMG_PATH" -nobrowse -readonly 2>>"$LOG_PATH") || fail "Не удалось смонтировать dmg."
        MOUNT_POINT=$(printf '%s\n' "$MOUNT_OUTPUT" | awk '/\/Volumes\// {{print substr($0, index($0, "/Volumes/")); exit}}')
        [ -n "$MOUNT_POINT" ] || fail "Не удалось определить точку монтирования dmg."
        NEW_APP=$(find "$MOUNT_POINT" -maxdepth 2 -name "$TARGET_NAME" -type d -print -quit)
        if [ -z "$NEW_APP" ]; then
            NEW_APP=$(find "$MOUNT_POINT" -maxdepth 2 -name "*.app" -type d -print -quit)
        fi
    fi
fi

[ -n "$NEW_APP" ] || fail "В архиве обновления не найден .app."

BACKUP_PATH="$TARGET_PATH.old"
rm -rf "$BACKUP_PATH" || fail "Не удалось удалить старую резервную копию."
if [ -d "$TARGET_PATH" ]; then
    mv "$TARGET_PATH" "$BACKUP_PATH" || fail "Не удалось убрать старое приложение."
fi
ditto "$NEW_APP" "$TARGET_PATH" || {{
    rm -rf "$TARGET_PATH"
    if [ -d "$BACKUP_PATH" ]; then
        mv "$BACKUP_PATH" "$TARGET_PATH"
    fi
    fail "Не удалось скопировать новую версию."
}}
rm -rf "$BACKUP_PATH"

if [ -n "$MOUNT_POINT" ]; then
    hdiutil detach "$MOUNT_POINT" >/dev/null 2>&1 || true
fi
rm -rf "$WORK_DIR"
log "updated $TARGET_PATH"
open "$TARGET_PATH" || log "failed to reopen $TARGET_PATH"
"#,
        url = shell_literal(download_url),
        sha256 = shell_literal(sha256),
        size = size,
        target = shell_literal(target.to_string_lossy()),
        target_name = shell_literal(target_name),
        pid = parent_pid,
        log_path = shell_literal(log_path.to_string_lossy()),
    )
}

#[tauri::command]
fn install_macos_update(
    app: tauri::AppHandle,
    url: String,
    sha256: String,
    size: u64,
) -> Result<bool, String> {
    if !url.starts_with("https://nfproject.ru/app/") {
        return Err("Недопустимый адрес обновления macOS.".to_string());
    }
    if sha256.len() != 64 || !sha256.bytes().all(|byte| byte.is_ascii_hexdigit()) || size == 0 {
        return Err("В манифесте отсутствуют данные проверки архива macOS.".to_string());
    }
    let executable_dir = app
        .path()
        .executable_dir()
        .map_err(|error| error.to_string())?;
    let Some(target) = macos_update_target(&executable_dir) else {
        return Ok(false);
    };
    let update_dir = app
        .path()
        .app_local_data_dir()
        .map_err(|error| error.to_string())?;
    fs::create_dir_all(&update_dir).map_err(|error| error.to_string())?;
    let script_path = update_dir.join("install-update.sh");
    let log_path = update_dir.join("update.log");
    let script =
        build_macos_updater_script(&url, &target, &sha256, size, &log_path, std::process::id());
    fs::write(&script_path, script).map_err(|error| error.to_string())?;
    // Keep the updater alive after plugin-process exits the application, matching
    // the detached process used by the legacy macOS updater.
    Command::new("/usr/bin/nohup")
        .arg("/bin/sh")
        .arg(&script_path)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(|error| error.to_string())?;
    Ok(true)
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
    let mut builder = tauri::Builder::default()
        .manage(BackendState::default())
        .plugin(tauri_plugin_single_instance::init(|app, _arguments, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_clipboard_manager::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_process::init())
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
                    architecture: std::env::consts::ARCH.to_string(),
                    development: cfg!(debug_assertions),
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
        });

    if native_updates_enabled() {
        builder = builder.plugin(tauri_plugin_updater::Builder::new().build());
    }

    let app = builder
        .invoke_handler(tauri::generate_handler![
            backend_connection,
            fetch_update_manifest,
            install_macos_update
        ])
        .build(tauri::generate_context!())
        .expect("failed to build the nfprogress desktop application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_backend(app_handle);
        }
    });
}
