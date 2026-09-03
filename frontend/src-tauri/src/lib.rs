use std::fmt::Write as _;
use std::fs;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use tauri::{Emitter, Manager, PhysicalPosition, PhysicalSize, RunEvent, State};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

#[derive(Serialize)]
struct SqliteEntityRow {
    id: String,
    project_id: Option<String>,
    name: Option<String>,
    goal: Option<f64>,
    infinite: i64,
    unit: String,
    status: String,
    created_at: Option<String>,
    updated_at: Option<String>,
    payload_json: String,
}

#[derive(Serialize)]
struct SqliteProgressRow {
    id: String,
    project_id: String,
    stage_id: Option<String>,
    created_at: Option<String>,
    added_symbols: Option<f64>,
    added_progress: Option<f64>,
    payload_json: String,
}

#[derive(Serialize)]
struct SqliteProjectReadModel {
    mirror_status: String,
    projects: Vec<SqliteEntityRow>,
    stages: Vec<SqliteEntityRow>,
    progress_entries: Vec<SqliteProgressRow>,
}

const BACKEND_HOST: &str = "127.0.0.1";
const BACKEND_START_TIMEOUT: Duration = Duration::from_secs(30);
const UPDATE_MANIFEST_URL: &str = "https://nfproject.ru/app/update_manifest.json";
const UPDATE_MANIFEST_TIMEOUT: Duration = Duration::from_secs(10);
const WINDOW_STATE_FILE: &str = "main-window.json";

#[derive(Clone, Deserialize, Serialize)]
struct MainWindowState {
    width: u32,
    height: u32,
    x: i32,
    y: i32,
}

impl MainWindowState {
    fn is_valid(&self) -> bool {
        (820..=10_000).contains(&self.width) && (600..=10_000).contains(&self.height)
    }
}

fn main_window_state_path(app: &tauri::AppHandle) -> Option<PathBuf> {
    app.path()
        .app_config_dir()
        .ok()
        .map(|directory| directory.join(WINDOW_STATE_FILE))
}

fn restore_main_window_state(app: &tauri::AppHandle) {
    let Some(path) = main_window_state_path(app) else {
        return;
    };
    let Ok(contents) = fs::read_to_string(path) else {
        return;
    };
    let Ok(state) = serde_json::from_str::<MainWindowState>(&contents) else {
        return;
    };
    if !state.is_valid() {
        return;
    }
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    let _ = window.set_size(PhysicalSize::new(state.width, state.height));
    let _ = window.set_position(PhysicalPosition::new(state.x, state.y));
}

fn save_main_window_state(app: &tauri::AppHandle) {
    let Some(window) = app.get_webview_window("main") else {
        return;
    };
    let (Ok(size), Ok(position)) = (window.inner_size(), window.outer_position()) else {
        return;
    };
    let state = MainWindowState {
        width: size.width,
        height: size.height,
        x: position.x,
        y: position.y,
    };
    if !state.is_valid() {
        return;
    }
    let Some(path) = main_window_state_path(app) else {
        return;
    };
    if fs::create_dir_all(path.parent().unwrap_or_else(|| Path::new("."))).is_err() {
        return;
    }
    let Ok(contents) = serde_json::to_string(&state) else {
        return;
    };
    let _ = fs::write(path, contents);
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BackendConnection {
    api_base_url: String,
    session_token: String,
    native_updates: bool,
    architecture: String,
    development: bool,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct MacosUpdateProgress {
    downloaded_bytes: u64,
    total_bytes: u64,
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

fn sqlite_data_root() -> Result<PathBuf, String> {
    if let Ok(path) = std::env::var("NFPROGRESS_DATA_DIR") {
        return Ok(PathBuf::from(path));
    }
    let home = dirs_fallback_home()?;
    let root = if cfg!(target_os = "windows") {
        std::env::var_os("APPDATA")
            .map(PathBuf::from)
            .unwrap_or_else(|| home.join("AppData").join("Roaming"))
            .join("nfprogress")
    } else if cfg!(target_os = "macos") {
        home.join("Documents").join("nfprogress")
    } else {
        let documents = home.join("Documents");
        if documents.exists() {
            documents.join("nfprogress")
        } else {
            home.join(".local").join("share").join("nfprogress")
        }
    };
    if cfg!(debug_assertions) {
        Ok(root.join("test_data"))
    } else {
        Ok(root)
    }
}

fn dirs_fallback_home() -> Result<PathBuf, String> {
    std::env::var_os("HOME")
        .or_else(|| std::env::var_os("USERPROFILE"))
        .map(PathBuf::from)
        .ok_or_else(|| "Не удалось определить домашнюю директорию пользователя.".to_string())
}

fn read_sqlite_entity_rows(
    connection: &rusqlite::Connection,
    table: &str,
) -> Result<Vec<SqliteEntityRow>, String> {
    let sql = match table {
        "projects" => "SELECT id, NULL, name, goal, infinite, unit, status, created_at, updated_at, payload_json FROM projects",
        "stages" => "SELECT id, project_id, name, goal, infinite, unit, status, created_at, updated_at, payload_json FROM stages ORDER BY rowid",
        _ => return Err("Недопустимая таблица SQLite.".to_string()),
    };
    let mut statement = connection.prepare(sql).map_err(|error| error.to_string())?;
    let rows = statement
        .query_map([], |row| {
            Ok(SqliteEntityRow {
                id: row.get(0)?,
                project_id: row.get(1)?,
                name: row.get(2)?,
                goal: row.get(3)?,
                infinite: row.get(4)?,
                unit: row.get(5)?,
                status: row.get(6)?,
                created_at: row.get(7)?,
                updated_at: row.get(8)?,
                payload_json: row.get(9)?,
            })
        })
        .map_err(|error| error.to_string())?;
    rows.map(|row| row.map_err(|error| error.to_string()))
        .collect()
}

#[tauri::command]
fn read_sqlite_projects() -> Result<SqliteProjectReadModel, String> {
    let database = sqlite_data_root()?.join("nfprogress.db");
    let connection =
        rusqlite::Connection::open_with_flags(database, rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY)
            .map_err(|error| error.to_string())?;
    let status: String = connection
        .query_row(
            "SELECT sync_status FROM mirror_state WHERE id = 1",
            [],
            |row| row.get(0),
        )
        .map_err(|error| error.to_string())?;
    if status != "healthy" {
        return Err(format!("SQLite mirror status is {status}"));
    }
    let mut progress = connection
        .prepare("SELECT id, project_id, stage_id, created_at, added_symbols, added_progress, payload_json FROM progress_entries ORDER BY rowid")
        .map_err(|error| error.to_string())?;
    let progress_entries = progress
        .query_map([], |row| {
            Ok(SqliteProgressRow {
                id: row.get(0)?,
                project_id: row.get(1)?,
                stage_id: row.get(2)?,
                created_at: row.get(3)?,
                added_symbols: row.get(4)?,
                added_progress: row.get(5)?,
                payload_json: row.get(6)?,
            })
        })
        .map_err(|error| error.to_string())?
        .map(|row| row.map_err(|error| error.to_string()))
        .collect::<Result<Vec<_>, _>>()?;
    Ok(SqliteProjectReadModel {
        mirror_status: status,
        projects: read_sqlite_entity_rows(&connection, "projects")?,
        stages: read_sqlite_entity_rows(&connection, "stages")?,
        progress_entries,
    })
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
            Path::new("/tmp/nfprogress-update.zip"),
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
        assert!(!script.contains("curl "));
    }

    #[cfg(debug_assertions)]
    #[test]
    fn tauri_dev_updates_the_installed_macos_app() {
        assert_eq!(
            macos_update_target(Path::new("/project/target/debug/nfprogress-desktop")),
            Some(Path::new("/Applications/nfprogress.app").to_path_buf()),
        );
    }

    #[test]
    fn packaged_macos_app_is_resolved_from_the_current_executable() {
        assert_eq!(
            macos_update_target(Path::new(
                "/Applications/nfprogress.app/Contents/MacOS/nfprogress-desktop",
            )),
            Some(Path::new("/Applications/nfprogress.app").to_path_buf()),
        );
    }

    #[cfg(target_os = "macos")]
    #[test]
    fn macos_updater_script_has_valid_shell_syntax() {
        let script = build_macos_updater_script(
            Path::new("/tmp/nfprogress-update.zip"),
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
    archive_path: &Path,
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
ARCHIVE_PATH={archive}
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
EXTRACT_DIR="$WORK_DIR/extract"
mkdir -p "$EXTRACT_DIR" || fail "Не удалось создать папку распаковки."

log "using downloaded archive $ARCHIVE_PATH"
[ -f "$ARCHIVE_PATH" ] || fail "Скачанный архив обновления не найден."
[ "$(stat -f %z "$ARCHIVE_PATH")" = "$SIZE" ] || fail "Размер архива обновления не совпадает с манифестом."
[ "$(shasum -a 256 "$ARCHIVE_PATH" | awk '{{print $1}}')" = "$SHA256" ] || fail "Контрольная сумма архива обновления не совпадает с манифестом."
ditto -x -k "$ARCHIVE_PATH" "$EXTRACT_DIR" || unzip -q "$ARCHIVE_PATH" -d "$EXTRACT_DIR" || fail "Не удалось распаковать zip-архив."

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
rm -f "$ARCHIVE_PATH"
log "updated $TARGET_PATH"
open "$TARGET_PATH" || log "failed to reopen $TARGET_PATH"
"#,
        archive = shell_literal(archive_path.to_string_lossy()),
        sha256 = shell_literal(sha256),
        size = size,
        target = shell_literal(target.to_string_lossy()),
        target_name = shell_literal(target_name),
        pid = parent_pid,
        log_path = shell_literal(log_path.to_string_lossy()),
    )
}

fn archive_sha256(path: &Path) -> Result<String, String> {
    let output = Command::new("/usr/bin/shasum")
        .args(["-a", "256"])
        .arg(path)
        .output()
        .map_err(|error| format!("Не удалось проверить SHA-256 обновления: {error}"))?;
    if !output.status.success() {
        return Err("Не удалось проверить SHA-256 обновления.".to_string());
    }
    String::from_utf8(output.stdout)
        .map_err(|error| format!("Некорректный результат проверки SHA-256: {error}"))?
        .split_whitespace()
        .next()
        .map(str::to_string)
        .ok_or_else(|| "Не удалось получить SHA-256 обновления.".to_string())
}

async fn download_macos_update(
    app: &tauri::AppHandle,
    url: &str,
    archive_path: &Path,
    expected_size: u64,
) -> Result<(), String> {
    configure_rustls_provider();
    let result = async {
        let client = reqwest::Client::builder()
            .connect_timeout(Duration::from_secs(20))
            .build()
            .map_err(|error| format!("Не удалось настроить загрузку обновления: {error}"))?;
        let mut response = client
            .get(url)
            .send()
            .await
            .map_err(|error| format!("Не удалось скачать обновление: {error}"))?
            .error_for_status()
            .map_err(|error| format!("Сервер обновлений вернул ошибку: {error}"))?;
        if response
            .content_length()
            .is_some_and(|content_length| content_length > expected_size)
        {
            return Err("Сервер объявил слишком большой размер обновления.".to_string());
        }

        let mut archive = fs::File::create(archive_path)
            .map_err(|error| format!("Не удалось создать архив обновления: {error}"))?;
        let mut downloaded = 0_u64;
        app.emit(
            "macos-update-progress",
            MacosUpdateProgress {
                downloaded_bytes: 0,
                total_bytes: expected_size,
            },
        )
        .map_err(|error| error.to_string())?;
        while let Some(chunk) = response
            .chunk()
            .await
            .map_err(|error| format!("Ошибка загрузки обновления: {error}"))?
        {
            downloaded = downloaded.saturating_add(chunk.len() as u64);
            if downloaded > expected_size {
                return Err("Загрузка превышает размер из манифеста.".to_string());
            }
            archive
                .write_all(&chunk)
                .map_err(|error| format!("Не удалось записать архив обновления: {error}"))?;
            app.emit(
                "macos-update-progress",
                MacosUpdateProgress {
                    downloaded_bytes: downloaded,
                    total_bytes: expected_size,
                },
            )
            .map_err(|error| error.to_string())?;
        }
        archive
            .sync_all()
            .map_err(|error| format!("Не удалось сохранить архив обновления: {error}"))?;
        if downloaded != expected_size {
            return Err(format!(
                "Размер обновления не совпадает: ожидалось {expected_size}, получено {downloaded}."
            ));
        }
        Ok(())
    }
    .await;
    if result.is_err() {
        let _ = fs::remove_file(archive_path);
    }
    result
}

#[tauri::command]
async fn install_macos_update(
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
    // Tauri's PathResolver::executable_dir is the user's bin directory and is
    // unsupported on macOS; current_exe resolves the running app bundle.
    let executable = std::env::current_exe().map_err(|error| error.to_string())?;
    let Some(target) = macos_update_target(&executable) else {
        return Ok(false);
    };
    let update_dir = app
        .path()
        .app_local_data_dir()
        .map_err(|error| error.to_string())?;
    fs::create_dir_all(&update_dir).map_err(|error| error.to_string())?;
    let script_path = update_dir.join("install-update.sh");
    let log_path = update_dir.join("update.log");
    let archive_path = update_dir.join("update.zip");
    download_macos_update(&app, &url, &archive_path, size).await?;
    let actual_sha256 = match archive_sha256(&archive_path) {
        Ok(value) => value,
        Err(error) => {
            let _ = fs::remove_file(&archive_path);
            return Err(error);
        }
    };
    if !actual_sha256.eq_ignore_ascii_case(&sha256) {
        let _ = fs::remove_file(&archive_path);
        return Err("Контрольная сумма архива обновления не совпадает с манифестом.".to_string());
    }
    let script = build_macos_updater_script(
        &archive_path,
        &target,
        &sha256,
        size,
        &log_path,
        std::process::id(),
    );
    if let Err(error) = fs::write(&script_path, script) {
        let _ = fs::remove_file(&archive_path);
        return Err(error.to_string());
    }
    // Keep the updater alive after plugin-process exits the application, matching
    // the detached process used by the legacy macOS updater.
    if let Err(error) = Command::new("/usr/bin/nohup")
        .arg("/bin/sh")
        .arg(&script_path)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
    {
        let _ = fs::remove_file(&archive_path);
        return Err(error.to_string());
    }
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
            restore_main_window_state(&app.handle());
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
            read_sqlite_projects,
            fetch_update_manifest,
            install_macos_update
        ])
        .build(tauri::generate_context!())
        .expect("failed to build the nfprogress desktop application");

    app.run(|app_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            save_main_window_state(app_handle);
            stop_backend(app_handle);
        }
    });
}
