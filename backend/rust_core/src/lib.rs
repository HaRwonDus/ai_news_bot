use pyo3::prelude::*;
use scraper::{Html, Selector};
use serde::Serialize;
use std::collections::HashSet;

#[derive(Serialize)]
struct NewsItem {
    title: String,
    url: String,
    content: String,
}

fn is_navigation_title(title: &str) -> bool {
    let title_lower = title.to_lowercase();
    title_lower.contains("überspringen")
        || title_lower.contains("navigation")
        || title_lower.contains("springen")
}

fn absolute_url(src: &str, href: &str) -> String {
    if href.starts_with("http") {
        return href.to_string();
    }

    let base = if src.contains("dw.com") {
        "https://www.dw.com"
    } else if src.contains("tagesschau.de") {
        "https://www.tagesschau.de"
    } else {
        src.trim_end_matches('/')
    };

    if href.starts_with('/') {
        format!("{base}{href}")
    } else {
        format!("{base}/{href}")
    }
}

#[pyfunction]
fn fetch_news() -> PyResult<String> {
    let sources = vec![
        "https://www.dw.com/de/themen/s-9077",
        "https://www.tagesschau.de/",
    ];

    let mut results = Vec::new();
    let mut seen_urls = HashSet::new();

    for src in sources {
        if let Ok(resp) = reqwest::blocking::get(src) {
            if let Ok(text) = resp.text() {
                let doc = Html::parse_document(&text);
                let selector = Selector::parse("a").unwrap();

                for element in doc.select(&selector).take(40) {
                    if let Some(title) = element.text().next() {
                        let title = title.trim();
                        if title.len() < 15 || is_navigation_title(title) {
                            continue;
                        }

                        if let Some(href) = element.value().attr("href") {
                            if href.starts_with('#') {
                                continue;
                            }

                            let url = absolute_url(src, href);
                            if !seen_urls.insert(url.clone()) {
                                continue;
                            }

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
    let mut seen_urls = HashSet::new();
    let keywords = [
        "artikel",
        "nachricht",
        "news",
        "story",
        "deutschland",
        "politik",
        "wirtschaft",
    ];

    for src in sources {
        if let Ok(resp) = reqwest::blocking::get(src) {
            if let Ok(text) = resp.text() {
                let doc = Html::parse_document(&text);
                let selector = Selector::parse("a").unwrap();

                for element in doc.select(&selector).take(100) {
                    if let Some(title) = element.text().next() {
                        let title = title.trim();
                        if title.len() < 15 || is_navigation_title(title) {
                            continue;
                        }

                        if let Some(href) = element.value().attr("href") {
                            if href.starts_with('#') {
                                continue;
                            }

                            let href_lower = href.to_lowercase();
                            if !keywords.iter().any(|&k| href_lower.contains(k)) {
                                continue;
                            }

                            let url = absolute_url(src, href);
                            if !seen_urls.insert(url.clone()) {
                                continue;
                            }

                            if let Ok(article_resp) = reqwest::blocking::get(&url) {
                                if let Ok(article_html) = article_resp.text() {
                                    let article_doc = Html::parse_document(&article_html);
                                    let paragraph_sel = Selector::parse("p").unwrap();
                                    let paragraphs: Vec<_> =
                                        article_doc.select(&paragraph_sel).collect();

                                    if paragraphs.len() < 3 {
                                        continue;
                                    }

                                    let mut content = String::new();
                                    for paragraph in paragraphs.iter().take(10) {
                                        let text =
                                            paragraph.text().collect::<Vec<_>>().join(" ");
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

    println!("Collected articles: {}", results.len());
    Ok(serde_json::to_string(&results).unwrap())
}

#[pymodule]
fn rust_core(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(fetch_news, m)?)?;
    m.add_function(wrap_pyfunction!(fetch_full_articles, m)?)?;
    Ok(())
}
