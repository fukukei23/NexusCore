from nexuscore.code_interpreter.sandbox_runner import SandboxRunner
from nexuscore.utils.logger import logger  # あなたのカスタムロガーを使用

from nexuscore.npe.engine import NPEEngine
from nexuscore.utils.test_generator import TestGenerator
from nexuscore.utils.vcs import GitController
from nexuscore.workflows.multi_llm_review import MultiLLMReviewer


class NexusOSKernel:
    """
    The central, trusted kernel for NexusOS.
    It exposes a set of "system calls" that higher-level agents can use,
    and provides access to trusted "services".
    """

    def __init__(self):
        """
        カーネルの起動時に、全てのコアモジュールをシングルトンとして初期化します。
        """
        logger.info("NexusOS Kernel v1.1 is booting...")

        # --- コア・カーネルモジュールの初期化 ---
        self.npe = NPEEngine()
        self.vcs = GitController()
        self.reviewer = MultiLLMReviewer()
        self.sandbox = SandboxRunner()
        self.testgen = TestGenerator()

        # --- サービス・レジストリ ---
        # OSが管理する、信頼できる共有サービスをここに登録します。
        # アプリケーションは、get_service()を通じてこれらのサービスを利用します。
        self._services = {
            "Google Search_tool": self._initialize_google_search(),
            "default_llm_client": self._initialize_default_llm(),
            # 将来的にデータベース接続などもここに追加できます。
            # "database_connection": self._initialize_database()
        }

        logger.info("NexusOS Kernel v1.1 has been initialized and is now running.")

    # --------------------------------------------------------------------------
    # Service Provider Methods
    # --------------------------------------------------------------------------

    def get_service(self, service_name: str):
        """
        [Kernel Service] Returns a trusted, pre-configured service instance.
        アプリケーションは、このメソッドを通じてOSの共有機能を利用します。
        """
        service = self._services.get(service_name)
        if not service:
            logger.error(f"Service '{service_name}' not found in Kernel registry.")
            raise ValueError(f"Service '{service_name}' not found.")

        logger.info(f"Kernel is providing service '{service_name}' to an application.")
        return service

    def _initialize_google_search(self):
        """（プレースホルダー）本物のGoogle Search APIクライアントを初期化します。"""
        logger.debug("Initializing Google Search service...")

        # from your_actual_google_search_library import GoogleSearchClient
        # return GoogleSearchClient(api_key=os.getenv("GOOGLE_API_KEY"))
        class DummySearchTool:
            def search(self, queries):
                logger.info(f"KERNEL_STUB (Search): Searching for: {queries}")
                return [
                    {
                        "title": "AI in Healthcare",
                        "snippet": "A growing market.",
                        "url": "http://example.com",
                    }
                ]

        return DummySearchTool()

    def _initialize_default_llm(self):
        """（プレースホルダー）本物のLLMクライアントを初期化します。"""
        logger.debug("Initializing Default LLM Client service...")

        # from your_actual_llm_library import LLMClient
        # return LLMClient(api_key=os.getenv("OPENAI_API_KEY"))
        class DummyLLMClient:
            def invoke(self, prompt, **kwargs):
                logger.info("KERNEL_STUB (LLM): Invoking LLM...")
                return """
                {
                    "ventureName": "HealthAI Diagnostics",
                    "marketAnalysis": "The market for AI-driven diagnostic tools is rapidly expanding.",
                    "productThesis": "An AI platform that analyzes medical images to provide preliminary diagnoses.",
                    "strategicFit": "Leverages NexusCore's data processing and UI generation capabilities.",
                    "resourceRequest": "1 CEO Agent, 5 Dev Agents, 4-week sprint for MVP.",
                    "projectedROI": "5-year 20x return potential."
                }
                """

        return DummyLLMClient()

    # --------------------------------------------------------------------------
    # System Call Methods
    # --------------------------------------------------------------------------

    def syscall_execute_code(self, agent_id: str, code: str, estimated_cost: float) -> dict:
        """
        [System Call] 全てのチェックを通過した後、コードを安全な環境で実行します。
        """
        logger.debug(f"Received 'execute_code' syscall from agent '{agent_id}'.")

        # 1. NPEによる予算・ポリシーチェック (関所)
        permission = self.npe.request_permission(
            agent_id=agent_id, action="execute_code", estimated_cost=estimated_cost
        )
        if not permission.is_granted:
            logger.warning(f"Syscall denied for {agent_id} by NPE: {permission.reason}")
            raise PermissionError(f"NPE denied request: {permission.reason}")

        # 2. サンドボックスでの実行
        result = self.sandbox.run(code)

        # 3. 監査ログの記録
        self.npe.log_transaction(agent_id, "execute_code", result)

        return result

    def syscall_commit_file(
        self, agent_id: str, file_path: str, file_content: str, commit_message: str
    ) -> dict:
        """
        [System Call] AIピアレビューと自動テストの後、ファイルを書き込み、VCSにコミットします。
        """
        logger.debug(
            f"Received 'commit_file' syscall from agent '{agent_id}' for path '{file_path}'."
        )

        # 1. NPEによるチェック
        permission = self.npe.request_permission(agent_id=agent_id, action="commit_file")
        if not permission.is_granted:
            logger.warning(f"Syscall denied for {agent_id} by NPE: {permission.reason}")
            raise PermissionError(f"NPE denied request: {permission.reason}")

        # 2. AIピアレビュー (必須プロセス)
        logger.info(f"Submitting code for file '{file_path}' to AI Peer Review...")
        review_result = self.reviewer.review(file_content)
        if not review_result.is_approved:
            logger.warning(f"Code for '{file_path}' was rejected by AI Peer Review.")
            raise ValueError(f"AI Peer Review rejected the code: {review_result.feedback}")
        logger.info(f"AI Peer Review approved code for '{file_path}'.")

        # 3. 自動テスト生成と実行
        logger.info(f"Generating and running tests for file '{file_path}'...")
        tests = self.testgen.generate(file_content)
        test_result = self.sandbox.run(tests)
        if not test_result.passed:
            logger.warning(f"Automated tests failed for '{file_path}'.")
            raise ValueError(f"Automated tests failed: {test_result.output}")
        logger.info(f"Automated tests passed for '{file_path}'.")

        # 4. VCSによるファイル書き込みとコミット
        logger.info(f"Committing file '{file_path}' to version control...")
        self.vcs.write_and_commit(
            path=file_path,
            content=review_result.approved_code,  # レビュー済みの承認されたコードを使用
            message=f"[{agent_id}] {commit_message}",
        )

        logger.info(f"File '{file_path}' committed successfully by '{agent_id}'.")
        return {"status": "success", "commit_hash": self.vcs.get_last_commit_hash()}


# --- シングルトンインスタンス ---
# OS全体で、カーネルはただ一つだけ存在し、どこからでも同じインスタンスが
# 参照されるようにします。
_kernel_instance = None


def get_kernel() -> NexusOSKernel:
    """
    Returns the singleton instance of the NexusOS Kernel.
    Initializes it on the first call.
    """
    global _kernel_instance
    if _kernel_instance is None:
        _kernel_instance = NexusOSKernel()
    return _kernel_instance
