//! Bounded Mind Elixir normalization and structural XMind import.
//!
//! The map payload is intentionally kept as an opaque JSON object.  Only the
//! fields needed by the editor and the map-note relation are validated or
//! normalized; all other fields travel through ordinary saves unchanged.

use std::collections::HashSet;
use std::io::{Cursor, Read};

use quick_xml::events::Event;
use quick_xml::Reader;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};
use zip::ZipArchive;

pub const MAX_MAP_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_MAP_NODES: usize = 50_000;
pub const MAX_MAP_DEPTH: usize = 512;
pub const MAX_TOPIC_LENGTH: usize = 300_000;
pub const MAX_XMIND_ARCHIVE_BYTES: usize = 50 * 1024 * 1024;
pub const MAX_XMIND_ENTRIES: usize = 2_048;
pub const MAX_XMIND_DECOMPRESSED_BYTES: u64 = 100 * 1024 * 1024;
pub const MAX_XMIND_CONTENT_BYTES: usize = 16 * 1024 * 1024;
pub const MAX_XMIND_SHEETS: usize = 100;

fn error(message: impl Into<String>) -> String {
    format!("Ошибка карты: {}", message.into())
}

fn object(value: &Value) -> Option<&Map<String, Value>> {
    value.as_object()
}

fn valid_text(value: &Value, field: &str) -> Result<String, String> {
    let text = value
        .as_str()
        .ok_or_else(|| error(format!("поле {field} должно быть текстом")))?;
    if text.chars().count() > MAX_TOPIC_LENGTH || text.contains('\0') {
        return Err(error(format!(
            "поле {field} слишком длинное или повреждено"
        )));
    }
    Ok(text.to_string())
}

fn validate_node(value: &Value, depth: usize, count: &mut usize) -> Result<(), String> {
    if depth > MAX_MAP_DEPTH {
        return Err(error("карта имеет слишком большую глубину"));
    }
    *count = count.saturating_add(1);
    if *count > MAX_MAP_NODES {
        return Err(error("карта содержит слишком много узлов"));
    }
    let node = object(value).ok_or_else(|| error("узел карты должен быть объектом"))?;
    let id = node
        .get("id")
        .and_then(Value::as_str)
        .filter(|value| !value.is_empty())
        .ok_or_else(|| error("узел карты не имеет стабильного id"))?;
    if id.chars().count() > 512 || id.contains('\0') {
        return Err(error("id узла карты слишком длинный"));
    }
    valid_text(
        node.get("topic")
            .ok_or_else(|| error("узел карты не имеет topic"))?,
        "topic",
    )?;
    let children = node
        .get("children")
        .and_then(Value::as_array)
        .ok_or_else(|| error("children узла карты должны быть массивом"))?;
    for child in children {
        validate_node(child, depth + 1, count)?;
    }
    Ok(())
}

fn normalize_free_node(value: &Value, is_root: bool, depth: usize) -> Option<Value> {
    let source = object(value)?;
    let id = source.get("id")?.as_str()?;
    let topic = source.get("topic")?.as_str()?;
    if id.is_empty()
        || id.chars().count() > 512
        || topic.contains('\0')
        || topic.chars().count() > MAX_TOPIC_LENGTH
    {
        return None;
    }
    if depth > MAX_MAP_DEPTH {
        return None;
    }
    let mut node = source.clone();
    let children = source
        .get("children")
        .and_then(Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(|item| normalize_free_node(item, false, depth + 1))
                .collect::<Vec<_>>()
        })
        .unwrap_or_default();
    node.insert("children".to_string(), Value::Array(children));
    if is_root {
        let position = source.get("position").and_then(Value::as_object);
        let x = position
            .and_then(|value| value.get("x"))
            .and_then(Value::as_f64)
            .unwrap_or(320.0);
        let y = position
            .and_then(|value| value.get("y"))
            .and_then(Value::as_f64)
            .unwrap_or(240.0);
        node.insert("position".to_string(), serde_json::json!({"x": x, "y": y}));
        node.insert("nfprogressFreeRoot".to_string(), Value::Bool(true));
    } else {
        node.remove("position");
        node.remove("nfprogressFreeRoot");
    }
    if !node.get("nfprogressNote").is_some_and(Value::is_boolean) {
        node.remove("nfprogressNote");
    }
    node.remove("parent");
    Some(Value::Object(node))
}

/// Validate and normalize only the historical editor-owned fields.
pub fn normalize(value: Value) -> Result<Value, String> {
    let mut normalized = value;
    if serde_json::to_vec(&normalized)
        .map_err(|_| error("данные карты нельзя представить в JSON"))?
        .len()
        > MAX_MAP_BYTES
    {
        return Err(error("данные карты слишком велики"));
    }
    let root = normalized
        .get("nodeData")
        .ok_or_else(|| error("карта не имеет nodeData"))?;
    let root_object = object(root).ok_or_else(|| error("nodeData карты должен быть объектом"))?;
    if root_object
        .get("id")
        .and_then(Value::as_str)
        .map_or(true, str::is_empty)
    {
        return Err(error("корневой узел карты не имеет стабильного id"));
    }
    valid_text(
        root_object
            .get("topic")
            .ok_or_else(|| error("корневой узел карты не имеет topic"))?,
        "topic",
    )?;
    let mut count = 0;
    validate_node(root, 0, &mut count)?;

    if let Some(items) = normalized.get("freeNodes") {
        if let Some(items) = items.as_array() {
            let free_nodes = items
                .iter()
                .filter_map(|item| normalize_free_node(item, true, 0))
                .collect::<Vec<_>>();
            normalized["freeNodes"] = Value::Array(free_nodes);
        } else {
            normalized
                .as_object_mut()
                .expect("map was validated as an object")
                .remove("freeNodes");
        }
    }
    if let Some(items) = normalized.get("nfprogressFloatingItems") {
        if let Some(items) = items.as_array() {
            let valid = items
                .iter()
                .filter_map(|item| {
                    let source = item.as_object()?;
                    let id = source.get("id")?.as_str()?;
                    let kind = source.get("kind")?.as_str()?;
                    let text = source.get("text")?.as_str()?;
                    let x = source.get("x")?.as_f64()?;
                    let y = source.get("y")?.as_f64()?;
                    if id.is_empty() || !matches!(kind, "node" | "note") || text.contains('\0') {
                        return None;
                    }
                    let mut item = source.clone();
                    item.insert("id".to_string(), Value::String(id.to_string()));
                    item.insert("kind".to_string(), Value::String(kind.to_string()));
                    item.insert("text".to_string(), Value::String(text.to_string()));
                    item.insert("x".to_string(), Value::from(x.clamp(0.0, 100.0)));
                    item.insert("y".to_string(), Value::from(y.clamp(0.0, 100.0)));
                    Some(Value::Object(item))
                })
                .collect::<Vec<_>>();
            let ids = valid
                .iter()
                .filter_map(|item| item.get("id").and_then(Value::as_str))
                .map(str::to_string)
                .collect::<HashSet<_>>();
            let valid = valid
                .into_iter()
                .map(|mut item| {
                    let keep_parent = item.get("kind").and_then(Value::as_str) == Some("node")
                        && item
                            .get("parentId")
                            .and_then(Value::as_str)
                            .is_some_and(|parent| {
                                ids.contains(parent)
                                    && item.get("id").and_then(Value::as_str) != Some(parent)
                            });
                    if !keep_parent {
                        item.as_object_mut()
                            .expect("floating item object")
                            .remove("parentId");
                    }
                    item
                })
                .collect::<Vec<_>>();
            normalized["nfprogressFloatingItems"] = Value::Array(valid);
        } else {
            normalized
                .as_object_mut()
                .expect("map was validated as an object")
                .remove("nfprogressFloatingItems");
        }
    }
    if let Some(items) = normalized.get("nfprogressFloatingLinks") {
        if let Some(items) = items.as_array() {
            normalized["nfprogressFloatingLinks"] = Value::Array(
                items
                    .iter()
                    .filter_map(|item| {
                        let source = item.as_object()?;
                        let id = source.get("id")?.as_str()?;
                        let from_type = source.get("fromType")?.as_str()?;
                        let from = source.get("from")?.as_str()?;
                        let to_type = source.get("toType")?.as_str()?;
                        let to = source.get("to")?.as_str()?;
                        if id.is_empty()
                            || !matches!(from_type, "floating" | "node")
                            || !matches!(to_type, "floating" | "node")
                            || from.is_empty()
                            || to.is_empty()
                            || (from_type == to_type && from == to)
                        {
                            return None;
                        }
                        Some(item.clone())
                    })
                    .collect(),
            );
        } else {
            normalized
                .as_object_mut()
                .expect("map was validated as an object")
                .remove("nfprogressFloatingLinks");
        }
    }
    Ok(normalized)
}

pub fn map_id(value: &Value) -> Option<&str> {
    value.get("nodeData")?.get("id")?.as_str()
}

pub fn has_content(value: Option<&Value>, root_topic: &str) -> bool {
    let Some(map) = value else { return false };
    let Ok(map) = normalize(map.clone()) else {
        return false;
    };
    let Some(root) = map.get("nodeData") else {
        return false;
    };
    if root.get("topic").and_then(Value::as_str) != Some(root_topic)
        || root
            .get("children")
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
        || map
            .get("arrows")
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
        || map
            .get("summaries")
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
        || map
            .get("freeNodes")
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
        || map
            .get("nfprogressFloatingItems")
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
        || map
            .get("nfprogressFloatingLinks")
            .and_then(Value::as_array)
            .is_some_and(|v| !v.is_empty())
    {
        return true;
    }
    root.as_object().is_some_and(|object| {
        object.iter().any(|(key, value)| {
            if matches!(
                key.as_str(),
                "id" | "topic" | "children" | "root" | "expanded" | "direction"
            ) {
                return false;
            }
            match value {
                Value::Null => false,
                Value::String(value) => !value.is_empty(),
                Value::Array(value) => !value.is_empty(),
                Value::Object(value) => !value.is_empty(),
                _ => true,
            }
        })
    })
}

pub fn extract_notes(value: &Value) -> Vec<(String, String)> {
    let mut result = Vec::new();
    let mut seen = HashSet::new();
    if let Some(items) = value
        .get("nfprogressFloatingItems")
        .and_then(Value::as_array)
    {
        for item in items {
            if item.get("kind").and_then(Value::as_str) == Some("note") {
                if let (Some(id), Some(text)) = (
                    item.get("id").and_then(Value::as_str),
                    item.get("text").and_then(Value::as_str),
                ) {
                    if seen.insert(id.to_string()) {
                        result.push((id.to_string(), text.to_string()));
                    }
                }
            }
        }
    }
    fn walk(value: &Value, result: &mut Vec<(String, String)>, seen: &mut HashSet<String>) {
        let Some(items) = value.as_array() else {
            return;
        };
        for item in items {
            if item.get("nfprogressNote").and_then(Value::as_bool) == Some(true) {
                if let (Some(id), Some(text)) = (
                    item.get("id").and_then(Value::as_str),
                    item.get("topic").and_then(Value::as_str),
                ) {
                    if seen.insert(id.to_string()) {
                        result.push((id.to_string(), text.to_string()));
                    }
                }
            }
            walk(item.get("children").unwrap_or(&Value::Null), result, seen);
        }
    }
    walk(
        value.get("freeNodes").unwrap_or(&Value::Null),
        &mut result,
        &mut seen,
    );
    result
}

pub fn set_note_text(value: &Value, node_id: &str, text: &str) -> Option<Value> {
    let mut map = normalize(value.clone()).ok()?;
    let clean = text
        .replace('\0', "")
        .chars()
        .take(MAX_TOPIC_LENGTH)
        .collect::<String>();
    fn native(nodes: &mut [Value], node_id: &str, text: &str) -> bool {
        for item in nodes {
            if item.get("id").and_then(Value::as_str) == Some(node_id)
                && item.get("nfprogressNote").and_then(Value::as_bool) == Some(true)
            {
                item["topic"] = Value::String(text.to_string());
                return true;
            }
            if let Some(children) = item.get_mut("children").and_then(Value::as_array_mut) {
                if native(children, node_id, text) {
                    return true;
                }
            }
        }
        false
    }
    if native(map.get_mut("freeNodes")?.as_array_mut()?, node_id, &clean) {
        return Some(map);
    }
    let items = map.get_mut("nfprogressFloatingItems")?.as_array_mut()?;
    for item in items {
        if item.get("id").and_then(Value::as_str) == Some(node_id)
            && item.get("kind").and_then(Value::as_str) == Some("note")
        {
            item["text"] = Value::String(clean);
            return Some(map);
        }
    }
    None
}

fn collect_node_ids(value: &Value, ids: &mut HashSet<String>) {
    if let Some(id) = value.get("id").and_then(Value::as_str) {
        ids.insert(id.to_string());
    }
    if let Some(children) = value.get("children").and_then(Value::as_array) {
        for child in children {
            collect_node_ids(child, ids);
        }
    }
}

pub fn remove_note(value: &Value, node_id: &str) -> Option<Value> {
    let mut map = normalize(value.clone()).ok()?;
    let mut removed = HashSet::new();
    fn remove_native(nodes: &mut Vec<Value>, node_id: &str, removed: &mut HashSet<String>) -> bool {
        let Some(index) = nodes.iter().position(|item| {
            item.get("id").and_then(Value::as_str) == Some(node_id)
                && item.get("nfprogressNote").and_then(Value::as_bool) == Some(true)
        }) else {
            for item in nodes {
                if let Some(children) = item.get_mut("children").and_then(Value::as_array_mut) {
                    if remove_native(children, node_id, removed) {
                        return true;
                    }
                }
            }
            return false;
        };
        collect_node_ids(&nodes[index], removed);
        nodes.remove(index);
        true
    }
    if let Some(nodes) = map.get_mut("freeNodes").and_then(Value::as_array_mut) {
        remove_native(nodes, node_id, &mut removed);
    }
    if let Some(items) = map
        .get_mut("nfprogressFloatingItems")
        .and_then(Value::as_array_mut)
    {
        if items.iter().any(|item| {
            item.get("id").and_then(Value::as_str) == Some(node_id)
                && item.get("kind").and_then(Value::as_str) == Some("note")
        }) {
            items.retain(|item| {
                !(item.get("id").and_then(Value::as_str) == Some(node_id)
                    && item.get("kind").and_then(Value::as_str) == Some("note"))
            });
            removed.insert(node_id.to_string());
        }
    }
    if removed.is_empty() {
        return None;
    }
    if let Some(items) = map.get_mut("arrows").and_then(Value::as_array_mut) {
        items.retain(|item| {
            !["from", "to"].iter().any(|key| {
                item.get(*key)
                    .and_then(Value::as_str)
                    .is_some_and(|id| removed.contains(id))
            })
        });
    }
    if let Some(items) = map.get_mut("summaries").and_then(Value::as_array_mut) {
        items.retain(|item| {
            !item
                .get("parent")
                .and_then(Value::as_str)
                .is_some_and(|id| removed.contains(id))
        });
    }
    if let Some(items) = map
        .get_mut("nfprogressFloatingLinks")
        .and_then(Value::as_array_mut)
    {
        items.retain(|item| {
            !["from", "to"].iter().any(|key| {
                item.get(*key)
                    .and_then(Value::as_str)
                    .is_some_and(|id| removed.contains(id))
            })
        });
    }
    Some(map)
}

#[derive(Debug)]
struct Topic {
    title: String,
    children: Vec<Topic>,
}

fn bounded_title(value: &str, context: &str) -> Result<String, String> {
    let title = value.replace('\0', "");
    if title.trim().is_empty() {
        return Err(error(format!("в XMind отсутствует название {context}")));
    }
    if title.chars().count() > MAX_TOPIC_LENGTH {
        return Err(error("тема XMind слишком длинная"));
    }
    Ok(title.trim().to_string())
}

fn json_topic(
    value: &Value,
    context: &str,
    depth: usize,
    count: &mut usize,
) -> Result<Topic, String> {
    if depth > MAX_MAP_DEPTH {
        return Err(error("XMind имеет слишком большую глубину"));
    }
    *count += 1;
    if *count > MAX_MAP_NODES {
        return Err(error("XMind содержит слишком много узлов"));
    }
    let source = object(value).ok_or_else(|| error(format!("некорректная тема {context}")))?;
    let title = bounded_title(
        source.get("title").and_then(Value::as_str).unwrap_or(""),
        context,
    )?;
    let mut children = Vec::new();
    if let Some(attached) = source
        .get("children")
        .and_then(Value::as_object)
        .and_then(|v| v.get("attached"))
    {
        let attached = attached
            .as_array()
            .ok_or_else(|| error(format!("некорректные дочерние узлы {context}")))?;
        for (index, child) in attached.iter().enumerate() {
            children.push(json_topic(
                child,
                &format!("{context}[{index}]"),
                depth + 1,
                count,
            )?);
        }
    }
    Ok(Topic { title, children })
}

fn parse_json(raw: &[u8]) -> Result<Vec<(String, Topic)>, String> {
    let payload: Value = serde_json::from_slice(raw)
        .map_err(|_| error("content.json содержит некорректный JSON"))?;
    let sheets = payload
        .as_array()
        .ok_or_else(|| error("в content.json не найден массив листов"))?;
    if sheets.is_empty() || sheets.len() > MAX_XMIND_SHEETS {
        return Err(error("недопустимое число листов XMind"));
    }
    let mut result = Vec::new();
    let mut count = 0;
    for (index, sheet) in sheets.iter().enumerate() {
        let source =
            object(sheet).ok_or_else(|| error(format!("некорректный лист XMind {index}")))?;
        let root = source
            .get("rootTopic")
            .ok_or_else(|| error(format!("в листе {index} отсутствует root topic")))?;
        let topic = json_topic(root, &format!("листа {index}"), 0, &mut count)?;
        let title = source
            .get("title")
            .and_then(Value::as_str)
            .unwrap_or(&topic.title);
        result.push((bounded_title(title, &format!("листа {index}"))?, topic));
    }
    Ok(result)
}

fn local_name(name: &[u8]) -> String {
    String::from_utf8_lossy(name)
        .rsplit(':')
        .next()
        .unwrap_or_default()
        .to_string()
}

fn parse_xml(raw: &[u8]) -> Result<Vec<(String, Topic)>, String> {
    let lowered = raw
        .iter()
        .map(|byte| byte.to_ascii_lowercase())
        .collect::<Vec<_>>();
    if lowered.windows(9).any(|window| window == b"<!doctype")
        || lowered.windows(8).any(|window| window == b"<!entity")
        || lowered.windows(5).any(|window| window == b"<!dtd")
    {
        return Err(error("XML DTD и внешние сущности запрещены"));
    }
    let mut reader = Reader::from_reader(Cursor::new(raw));
    reader.config_mut().trim_text(true);
    let mut buffer = Vec::new();
    let mut sheets: Vec<(String, Option<Topic>)> = Vec::new();
    let mut topics: Vec<Topic> = Vec::new();
    let mut attached_depth = 0usize;
    let mut in_title = false;
    let mut title = String::new();
    let mut count = 0usize;
    loop {
        match reader.read_event_into(&mut buffer) {
            Ok(Event::Start(event)) => match local_name(event.name().as_ref()).as_str() {
                "sheet" => {
                    if sheets.len() >= MAX_XMIND_SHEETS {
                        return Err(error("в XMind слишком много листов"));
                    }
                    let sheet_title = event
                        .attributes()
                        .flatten()
                        .find(|a| a.key.as_ref() == b"title")
                        .and_then(|a| String::from_utf8(a.value.into_owned()).ok())
                        .unwrap_or_default();
                    sheets.push((sheet_title, None));
                }
                "topic" => {
                    if topics.len() >= MAX_MAP_DEPTH {
                        return Err(error("XMind имеет слишком большую глубину"));
                    }
                    topics.push(Topic {
                        title: String::new(),
                        children: Vec::new(),
                    });
                    count += 1;
                    if count > MAX_MAP_NODES {
                        return Err(error("XMind содержит слишком много узлов"));
                    }
                }
                "topics"
                    if event
                        .attributes()
                        .flatten()
                        .any(|a| a.key.as_ref() == b"type" && a.value.as_ref() == b"attached") =>
                {
                    attached_depth += 1
                }
                "title" => {
                    in_title = true;
                    title.clear();
                }
                _ => {}
            },
            Ok(Event::Text(event)) if in_title => title.push_str(
                &event
                    .xml10_content()
                    .map_err(|_| error("некорректный текст XML"))?,
            ),
            Ok(Event::End(event)) => match local_name(event.name().as_ref()).as_str() {
                "title" => {
                    if in_title {
                        if let Some(topic) = topics.last_mut() {
                            topic.title = title.clone();
                        } else if !sheets.is_empty() {
                            sheets.last_mut().expect("sheet").0 = title.clone();
                        }
                    }
                    in_title = false;
                }
                "topics" if attached_depth > 0 => attached_depth -= 1,
                "topic" => {
                    let topic = topics
                        .pop()
                        .ok_or_else(|| error("повреждённая структура XML"))?;
                    let topic = Topic {
                        title: bounded_title(&topic.title, "XML темы")?,
                        children: topic.children,
                    };
                    if attached_depth > 0 {
                        if let Some(parent) = topics.last_mut() {
                            parent.children.push(topic);
                        }
                    } else if let Some(sheet) = sheets.last_mut() {
                        sheet.1 = Some(topic);
                    }
                }
                _ => {}
            },
            Ok(Event::Empty(event)) => match local_name(event.name().as_ref()).as_str() {
                "sheet" => {
                    if sheets.len() >= MAX_XMIND_SHEETS {
                        return Err(error("в XMind слишком много листов"));
                    }
                    let sheet_title = event
                        .attributes()
                        .flatten()
                        .find(|a| a.key.as_ref() == b"title")
                        .and_then(|a| String::from_utf8(a.value.into_owned()).ok())
                        .unwrap_or_default();
                    sheets.push((sheet_title, None));
                }
                "topic" => {
                    count += 1;
                    if count > MAX_MAP_NODES {
                        return Err(error("XMind содержит слишком много узлов"));
                    }
                    return Err(error("в XML темы отсутствует название"));
                }
                _ => {}
            },
            Ok(Event::Eof) => break,
            Err(_) => return Err(error("content.xml содержит некорректный XML")),
            _ => {}
        }
        buffer.clear();
    }
    if sheets.is_empty() {
        return Err(error("в content.xml не найдено ни одного листа"));
    }
    sheets
        .into_iter()
        .enumerate()
        .map(|(index, (title, root))| {
            let root =
                root.ok_or_else(|| error(format!("в листе {index} отсутствует корневая тема")))?;
            let title = bounded_title(
                if title.is_empty() {
                    &root.title
                } else {
                    &title
                },
                &format!("листа {index}"),
            )?;
            Ok((title, root))
        })
        .collect()
}

fn stable_id(seed: &str) -> String {
    let mut digest = Sha256::new();
    digest.update(seed.as_bytes());
    format!("xmind-{:x}", digest.finalize())
}

pub fn linked_note_id(node_id: &str) -> String {
    format!("mindmap-{}", hex_digest(node_id))
}

fn hex_digest(seed: &str) -> String {
    let mut digest = Sha256::new();
    digest.update(seed.as_bytes());
    format!("{:x}", digest.finalize())[..28].to_string()
}

fn bytes_digest(bytes: &[u8]) -> String {
    let mut digest = Sha256::new();
    digest.update(bytes);
    format!("{:x}", digest.finalize())[..28].to_string()
}

fn to_map(topic: &Topic, namespace: &str, path: &str) -> Value {
    serde_json::json!({
        "id": stable_id(&format!("{namespace}/{path}")),
        "topic": topic.title,
        "children": topic.children.iter().enumerate().map(|(index, child)| to_map(child, namespace, &format!("{path}/{index}"))).collect::<Vec<_>>()
    })
}

/// Parse only the structural tree.  Attachments, images, relationships and
/// styling are intentionally deferred and never fetched or executed.
pub fn import_xmind(bytes: &[u8]) -> Result<Vec<Value>, String> {
    if bytes.len() > MAX_XMIND_ARCHIVE_BYTES {
        return Err(error("файл XMind слишком большой"));
    }
    let mut archive = ZipArchive::new(Cursor::new(bytes))
        .map_err(|_| error("файл XMind повреждён или не является ZIP"))?;
    if archive.len() == 0 || archive.len() > MAX_XMIND_ENTRIES {
        return Err(error("архив XMind содержит недопустимое число файлов"));
    }
    let mut names = HashSet::new();
    let mut total = 0u64;
    let mut json_index = None;
    let mut xml_index = None;
    for index in 0..archive.len() {
        let file = archive
            .by_index(index)
            .map_err(|_| error("не удалось проверить архив XMind"))?;
        let name = file.name().replace('\\', "/");
        if !names.insert(name.clone())
            || name.starts_with('/')
            || name.split('/').any(|part| part == "..")
            || name.contains(':')
            || file.enclosed_name().is_none()
        {
            return Err(error("архив XMind содержит небезопасный путь"));
        }
        total = total.saturating_add(file.size());
        if total > MAX_XMIND_DECOMPRESSED_BYTES {
            return Err(error("распакованный XMind слишком велик"));
        }
        if name == "content.json" {
            json_index = Some(index);
        } else if name == "content.xml" {
            xml_index = Some(index);
        }
    }
    let (index, name) = if let Some(index) = json_index {
        (index, "content.json")
    } else if let Some(index) = xml_index {
        (index, "content.xml")
    } else {
        return Err(error("в XMind отсутствует content.json или content.xml"));
    };
    let file = archive
        .by_index(index)
        .map_err(|_| error("не удалось открыть структуру XMind"))?;
    if file.size() as usize > MAX_XMIND_CONTENT_BYTES {
        return Err(error("структура XMind слишком велика"));
    }
    let mut raw = Vec::with_capacity(file.size() as usize);
    file.take((MAX_XMIND_CONTENT_BYTES + 1) as u64)
        .read_to_end(&mut raw)
        .map_err(|_| error("не удалось прочитать структуру XMind"))?;
    if raw.len() > MAX_XMIND_CONTENT_BYTES {
        return Err(error("структура XMind слишком велика"));
    }
    let sheets = if name.ends_with(".json") {
        parse_json(&raw)?
    } else {
        parse_xml(&raw)?
    };
    let namespace = bytes_digest(bytes);
    Ok(sheets
        .into_iter()
        .enumerate()
        .map(|(index, (title, root))| {
            serde_json::json!({
                "title": title,
                "data": { "nodeData": to_map(&root, &namespace, &format!("sheet/{index}")) }
            })
        })
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    fn archive(entries: &[(&str, &[u8])]) -> Vec<u8> {
        use zip::write::{SimpleFileOptions, ZipWriter};
        use zip::CompressionMethod;

        let cursor = Cursor::new(Vec::new());
        let mut writer = ZipWriter::new(cursor);
        let options = SimpleFileOptions::default().compression_method(CompressionMethod::Stored);
        for (name, content) in entries {
            writer.start_file(*name, options).unwrap();
            writer.write_all(content).unwrap();
        }
        writer.finish().unwrap().into_inner()
    }

    fn map() -> Value {
        serde_json::json!({"nodeData":{"id":"root","topic":"Root","children":[]},"unknown":{"keep":true}})
    }

    #[test]
    fn normalization_preserves_unknown_fields_and_ids() {
        let result = normalize(map()).unwrap();
        assert_eq!(result["nodeData"]["id"], "root");
        assert_eq!(result["unknown"]["keep"], true);
    }

    #[test]
    fn note_round_trip_matches_legacy_semantics() {
        let value = serde_json::json!({"nodeData":{"id":"root","topic":"Root","children":[]},"freeNodes":[{"id":"note","topic":"Old","children":[],"nfprogressNote":true}]});
        let updated = set_note_text(&value, "note", "New").unwrap();
        assert_eq!(extract_notes(&updated), vec![("note".into(), "New".into())]);
        assert!(remove_note(&updated, "note").unwrap()["freeNodes"]
            .as_array()
            .unwrap()
            .is_empty());
    }

    #[test]
    fn xmind_json_preserves_tree_order_and_uses_deterministic_ids() {
        let raw = serde_json::to_vec(&serde_json::json!([{
            "title": "Sheet",
            "rootTopic": {
                "id": "external-root",
                "title": "Root",
                "children": {"attached": [
                    {"title": "First"},
                    {"title": "Second", "children": {"attached": [{"title": "Nested"}]}}
                ]}
            }
        }]))
        .unwrap();
        let first = import_xmind(&archive(&[("content.json", &raw)])).unwrap();
        let second = import_xmind(&archive(&[("content.json", &raw)])).unwrap();
        assert_eq!(first, second);
        assert_eq!(
            first[0]["data"]["nodeData"]["children"][0]["topic"],
            "First"
        );
        assert_eq!(
            first[0]["data"]["nodeData"]["children"][1]["children"][0]["topic"],
            "Nested"
        );
        assert_ne!(first[0]["data"]["nodeData"]["id"], "external-root");
    }

    #[test]
    fn xmind_xml_supports_namespaces_and_rejects_entities() {
        let raw = br#"<xmap-content xmlns="urn:xmind"><sheet title="XML"><topic><title>Root</title><children><topics type="attached"><topic><title>Child</title></topic></topics></children></topic></sheet></xmap-content>"#;
        let result = import_xmind(&archive(&[("content.xml", raw)])).unwrap();
        assert_eq!(
            result[0]["data"]["nodeData"]["children"][0]["topic"],
            "Child"
        );
        let hostile = br#"<!DOCTYPE x [<!ENTITY e "network">]><xmap-content/>"#;
        assert!(import_xmind(&archive(&[("content.xml", hostile)])).is_err());
    }

    #[test]
    fn xmind_archive_rejects_traversal_and_excessive_sheets() {
        let content = br#"[{"title":"Sheet","rootTopic":{"title":"Root"}}]"#;
        assert!(import_xmind(&archive(&[("../content.json", content)])).is_err());
        let too_many = (0..=MAX_XMIND_SHEETS)
            .map(|index| serde_json::json!({"title": index, "rootTopic": {"title": "Root"}}))
            .collect::<Vec<_>>();
        let raw = serde_json::to_vec(&too_many).unwrap();
        assert!(import_xmind(&archive(&[("content.json", &raw)])).is_err());
    }
}
