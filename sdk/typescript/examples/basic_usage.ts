#!/usr/bin/env node
/**
 * NexusCore TypeScript SDK の基本的な使用例
 *
 * このサンプルコードは、NexusCore API の基本的な使用方法を示します。
 *
 * 実行方法:
 *   export NEXUSCORE_API_KEY='your-api-key'
 *   export FASTAPI_BASE_URL='http://localhost:8000'
 *   npx ts-node examples/basic_usage.ts
 */

import { Configuration, ProjectsApi, ProjectSummary } from '../index';

async function main() {
    // API Key を環境変数から取得（または明示的に指定）
    const apiKey = process.env.NEXUSCORE_API_KEY || 'your-api-key-here';
    const baseUrl = process.env.FASTAPI_BASE_URL || 'http://localhost:8000';

    if (apiKey === 'your-api-key-here') {
        console.error('⚠️  Warning: Using placeholder API key. Set NEXUSCORE_API_KEY environment variable.');
        console.error('   Example: export NEXUSCORE_API_KEY=\'your-actual-api-key\'');
        process.exit(1);
    }

    console.log(`🔗 Connecting to ${baseUrl}...`);
    console.log(`🔑 Using API Key: ${apiKey.substring(0, 10)}...`);

    // Configuration を作成
    const configuration = new Configuration({
        basePath: baseUrl,
        apiKey: apiKey,
    });

    try {
        // ProjectsApi インスタンスを作成
        const projectsApi = new ProjectsApi(configuration);

        console.log('\n📋 Fetching projects list...');

        // プロジェクト一覧を取得
        try {
            const response = await projectsApi.listProjectsApiV1ProjectsGet(
                apiKey,
                {}
            );

            console.log(`✅ Success! Found ${response.data.projects.length} project(s):\n`);

            if (response.data.projects.length === 0) {
                console.log('  (No projects found)');
            } else {
                response.data.projects.forEach((project: ProjectSummary) => {
                    console.log(`  📁 ${project.name}`);
                    console.log(`     ID: ${project.id}`);
                    if (project.repo_url) {
                        console.log(`     Repo: ${project.repo_url}`);
                    }
                    if (project.local_path) {
                        console.log(`     Path: ${project.local_path}`);
                    }
                    console.log();
                });
            }
        } catch (error: any) {
            console.error(`❌ API Error: ${error.response?.status || 'Unknown'} - ${error.message}`);
            if (error.response?.data) {
                console.error(`   Response:`, JSON.stringify(error.response.data, null, 2));
            }
            process.exit(1);
        }
    } catch (error: any) {
        console.error(`❌ Failed to create API client: ${error.message}`);
        process.exit(1);
    }
}

main().catch((error) => {
    console.error('❌ Unexpected error:', error);
    process.exit(1);
});

