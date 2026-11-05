mod bot;
mod bot_tests;
mod gametests;
mod harness;
mod parity;

use std::{net::SocketAddr, process::ExitCode, sync::Arc, time::Instant};

use pumpkin_core::server::Server;
use pumpkin_gametest::GameTestRunner;
use tokio::net::TcpListener;
use tokio_util::{sync::CancellationToken, task::TaskTracker};

async fn run_all_suites(server: &Arc<Server>, addr: SocketAddr) -> Result<Vec<String>, String> {
    let mut summary_lines = Vec::new();
    let mut runner = GameTestRunner::new();

    bot_tests::run_bot_tests(server, addr, &mut runner, &mut summary_lines).await?;
    gametests::run_gametests(server, &mut runner, &mut summary_lines).await?;

    Ok(summary_lines)
}

#[expect(
    clippy::print_stdout,
    clippy::print_stderr,
    reason = "CLI test runner outputs results to stdout/stderr"
)]
#[tokio::main]
async fn main() -> ExitCode {
    let _ = rustls::crypto::ring::default_provider().install_default();
    let _ = rayon::ThreadPoolBuilder::new()
        .thread_name(|i| format!("Rayon-Tester-{i}"))
        .build_global();

    let start = Instant::now();
    println!("Starting pumpkin-tester (single server + headless bots + Mojang GameTests)...");

    let temp_dir = match tempfile::tempdir() {
        Ok(dir) => dir,
        Err(err) => {
            eprintln!("Failed to create temporary world directory: {err}");
            return ExitCode::FAILURE;
        }
    };

    let server = match harness::create_test_server(&temp_dir).await {
        Ok(s) => s,
        Err(err) => {
            eprintln!("{err}");
            return ExitCode::FAILURE;
        }
    };

    harness::prepare_spawn_chunk(&server).await;

    // `pumpkin-tester --parity <report.json>` runs only the MineHouse
    // vanilla-parity GameTests and writes one result per test.
    let args: Vec<String> = std::env::args().collect();
    if let Some(i) = args.iter().position(|a| a == "--parity") {
        let out = args
            .get(i + 1)
            .cloned()
            .unwrap_or_else(|| "parity-pumpkin.json".into());
        let results = parity::run_parity(&server).await;
        server.shutdown().await;
        return match results {
            Ok(results) => {
                let json: Vec<_> = results
                    .iter()
                    .map(|r| {
                        println!("{} {}", if r.passed { "PASS" } else { "FAIL" }, r.test_id);
                        for m in &r.messages {
                            println!("    {m}");
                        }
                        serde_json::json!({ "test": r.test_id, "passed": r.passed, "messages": r.messages })
                    })
                    .collect();
                if let Err(err) = std::fs::write(
                    &out,
                    serde_json::to_string_pretty(&json).unwrap_or_default(),
                ) {
                    eprintln!("Failed to write {out}: {err}");
                    return ExitCode::FAILURE;
                }
                println!("Wrote {} parity results to {out}", json.len());
                ExitCode::SUCCESS
            }
            Err(err) => {
                eprintln!("parity suite failed: {err}");
                ExitCode::FAILURE
            }
        };
    }

    let listener = match TcpListener::bind("127.0.0.1:0").await {
        Ok(l) => l,
        Err(err) => {
            eprintln!("Failed to bind local TCP listener: {err}");
            return ExitCode::FAILURE;
        }
    };
    let local_addr = match listener.local_addr() {
        Ok(addr) => addr,
        Err(err) => {
            eprintln!("Failed to query local TCP address: {err}");
            return ExitCode::FAILURE;
        }
    };

    let cancel = CancellationToken::new();
    let tasks = TaskTracker::new();
    harness::spawn_java_listener(listener, server.clone(), cancel.clone(), &tasks);

    let result = run_all_suites(&server, local_addr).await;

    cancel.cancel();
    for player in server.get_all_players() {
        player.remove().await;
        server.remove_player(&player);
    }
    tasks.close();
    tasks.wait().await;
    server.shutdown().await;

    match result {
        Ok(lines) => {
            for line in lines {
                println!("{line}");
            }
            println!(
                "All bot integration tests and Mojang GameTests passed in {}ms!",
                start.elapsed().as_millis()
            );
            ExitCode::SUCCESS
        }
        Err(err) => {
            eprintln!("pumpkin-tester FAILED:\n{err}");
            ExitCode::FAILURE
        }
    }
}
