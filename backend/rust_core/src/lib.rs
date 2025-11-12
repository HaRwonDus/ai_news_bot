use pyo3::prelude::*;
use scraper::{Html, Selector};
use serde::Serialize;

#[derive(Serialize)]
struct NewsItem {
    title: String,
    url: String,
    content: String,
}

#[pyfunction]
fn fetch_news() -> PyResult<String> {
    let sources = vec![
        "https://www.dw.com/de/themen/s-9077",
        "https://www.tagesschau.de/",
    ];

    let mut results = Vec::new();

    for src in sources {
        if let Ok(resp) = reqwest::blocking::get(src) {
            if let Ok(text) = resp.text() {
                let doc = Html::parse_document(&text);
                let selector = Selector::parse("a").unwrap();

                for element in doc.select(&selector).take(20) {
                    if let Some(title) = element.text().next() {
                        let title = title.trim();
                        if title.len() < 15 { continue; }
                        if title.contains("springen") || title.contains("navigation") { continue; }

                        if let Some(href) = element.value().attr("href") {
                            let url = if href.starts_with("http") {
                                href.to_string()
                            } else {
                                format!("{src}{href}")
                            };
                            results.push(NewsItem {
                                title: title.to_string(),
                                url,
                                content: String::new(),
                            });
                        }
                    }
                }
            }
        }
    }

    Ok(serde_json::to_string(&results).unwrap())
}

#[pyfunction]
fn fetch_full_articles() -> PyResult<String> {
    let sources = vec![
        "https://www.dw.com/de/themen/s-9077",
        "https://www.tagesschau.de/",
    ];

    let mut results = Vec::new();
    let keywords = ["artikel", "nachricht", "news", "story", "deutschland", "politik", "wirtschaft"];

    for src in sources {
        if let Ok(resp) = reqwest::blocking::get(src) {
            if let Ok(text) = resp.text() {
                let doc = Html::parse_document(&text);
                let selector = Selector::parse("a").unwrap();

                for element in doc.select(&selector).take(80) {
                    if let Some(title) = element.text().next() {
                        let title = title.trim();

                        // фильтрация коротких заголовков
                        if title.len() < 15 { continue; }

                        if let Some(href) = element.value().attr("href") {
                            let href_lower = href.to_lowercase();
                            if !keywords.iter().any(|&k| href_lower.contains(k)) {
                                continue;
                            }

                            let url = if href.starts_with("http") {
                                href.to_string()
                            } else {
                                format!("{src}{href}")
                            };

                            if let Ok(article_resp) = reqwest::blocking::get(&url) {
                                if let Ok(article_html) = article_resp.text() {
                                    let article_doc = Html::parse_document(&article_html);
                                    let paragraph_sel = Selector::parse("p").unwrap();
                                    let paragraphs: Vec<_> = article_doc.select(&paragraph_sel).collect();

                                    // фильтр по количеству параграфов
                                    if paragraphs.len() < 3 { continue; }

                                    let mut content = String::new();
                                    for p in paragraphs.iter().take(10) {
                                        let text = p.text().collect::<Vec<_>>().join(" ");
                                        content.push_str(&format!("{} ", text.trim()));
                                    }

                                    if content.len() > 300 {
                                        results.push(NewsItem {
                                            title: title.to_string(),
                                            url,
                                            content,
                                        });
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    println!("✅ Собрано статей: {}", results.len());
    Ok(serde_json::to_string(&results).unwrap())
}

#[pymodule]
fn rust_core(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fetch_news, m)?)?;
    m.add_function(wrap_pyfunction!(fetch_full_articles, m)?)?;
    Ok(())
}
