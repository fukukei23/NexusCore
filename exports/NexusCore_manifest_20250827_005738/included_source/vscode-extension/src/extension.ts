// ==============================================================================
// フォルダ: vscode-extension/src
// ファイル名: extension.ts
// メモ: 【APIクライアント版】NexusCore APIサーバーと通信し、
//      自律的な開発タスクの実行と進捗管理を行うVSCode拡張機能の本体。
// ==============================================================================

import * as vscode from 'vscode';

// node-fetch v3はESMモジュールなので、CommonJSプロジェクトで使うために動的インポートを使用します。
// package.jsonに "node-fetch": "^3.3.2" が必要です。
type Fetch = typeof import('node-fetch').default;
let fetch: Fetch;

// APIサーバーのベースURL
const API_BASE_URL = 'http://127.0.0.1:5001';

// 拡張機能が有効化されたときに一度だけ実行される関数
export async function activate(context: vscode.ExtensionContext) {
    // node-fetchを動的にインポート
    try {
        fetch = (await import('node-fetch')).default;
    } catch (err) {
        vscode.window.showErrorMessage('Failed to load node-fetch. Please ensure it is installed.');
        return;
    }

    console.log('Congratulations, your extension "nexuscore-client" is now active!');

    // "nexuscore.executeTask" というコマンドを登録します。
    // このコマンドは package.json で定義されています。
    let disposable = vscode.commands.registerCommand('nexuscore.executeTask', async () => {
        
        // ユーザーに開発要求を入力してもらう
        const requirement = await vscode.window.showInputBox({
            prompt: 'どのようなアプリケーションを開発しますか？ (例: ユーザーを追加・表示できる簡単なCRMアプリ)',
            placeHolder: '開発要求を自然言語で入力してください。'
        });

        if (!requirement) {
            vscode.window.showInformationMessage('タスクがキャンセルされました。');
            return;
        }

        // 現在開いているワークスペースのパスを取得
        const workspaceFolders = vscode.workspace.workspaceFolders;
        if (!workspaceFolders || workspaceFolders.length === 0) {
            vscode.window.showErrorMessage('プロジェクトフォルダが開かれていません。');
            return;
        }
        const projectPath = workspaceFolders[0].uri.fsPath;

        // VSCodeのプログレス表示機能を使って、ユーザーに進捗を知らせる
        vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "NexusCoreがタスクを実行中...",
            cancellable: true
        }, async (progress, token) => {
            let taskId: string | null = null;

            token.onCancellationRequested(() => {
                // TODO: 将来的にAPIにキャンセルリクエストを送信する機能を実装
                console.log("User canceled the long running operation");
            });

            try {
                // --- Step 1: APIサーバーにタスク実行をリクエスト ---
                progress.report({ increment: 0, message: "APIサーバーに接続中..." });

                const executeResponse = await fetch(`${API_BASE_URL}/api/v1/execute`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        requirement: requirement,
                        project_path: projectPath
                    })
                });

                if (!executeResponse.ok) {
                    throw new Error(`APIサーバーへのリクエストに失敗しました: ${executeResponse.statusText}`);
                }

                const executeResult = await executeResponse.json() as { task_id: string };
                taskId = executeResult.task_id;
                progress.report({ increment: 10, message: `タスク開始 (ID: ${taskId.substring(0, 8)})...` });

                // --- Step 2: タスクのステータスを定期的にポーリング ---
                let isTaskFinished = false;
                while (!isTaskFinished && !token.isCancellationRequested) {
                    // 2秒待機
                    await new Promise(resolve => setTimeout(resolve, 2000));

                    const statusResponse = await fetch(`${API_BASE_URL}/api/v1/status/${taskId}`);
                    if (!statusResponse.ok) {
                        // 404の場合はタスクがまだ登録されていない可能性があるので少し待つ
                        if (statusResponse.status === 404) {
                            continue;
                        }
                        throw new Error(`ステータス確認に失敗: ${statusResponse.statusText}`);
                    }
                    
                    const statusResult = await statusResponse.json() as { status: string, message: string };

                    // 進捗メッセージを更新
                    progress.report({ message: statusResult.message });

                    switch (statusResult.status) {
                        case 'completed':
                            isTaskFinished = true;
                            vscode.window.showInformationMessage(`✅ NexusCoreタスク完了: ${statusResult.message}`);
                            break;
                        case 'error':
                            isTaskFinished = true;
                            vscode.window.showErrorMessage(`❌ NexusCoreタスクエラー: ${statusResult.message}`);
                            break;
                        case 'running':
                            // 実行中はポーリングを継続
                            break;
                    }
                }

            } catch (error: any) {
                vscode.window.showErrorMessage(`NexusCore拡張機能エラー: ${error.message}`);
            }

            // プログレス表示を終了
            return;
        });
    });

    // コマンドを拡張機能のコンテキストに登録
    context.subscriptions.push(disposable);
}

// 拡張機能が無効化されたときに実行される関数
export function deactivate() {}
