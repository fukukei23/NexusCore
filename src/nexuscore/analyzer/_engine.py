"""Core parsing engine and result data class for the analyzer."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from typing import Any

from ._config import CONFIG, TREE_SITTER_AVAILABLE, logger

if TREE_SITTER_AVAILABLE:
    from tree_sitter import Node, Query


class AnalysisResult:
    def __init__(self, success: bool = False, **kwargs):
        self.success = success
        self.timestamp = datetime.now().isoformat()
        self.data = kwargs

    def __getitem__(self, key):
        return self.data.get(key)

    def to_dict(self) -> dict[str, Any]:
        return {"success": self.success, "timestamp": self.timestamp, **self.data}

    def to_json(self, indent=2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class TreeSitterEngine:
    """Tree-sitter-based core parsing engine."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = {**CONFIG, **(config or {})}
        self.parsers: dict[str, Any] = {}
        self.languages: dict[str, Any] = {}

    def setup_parsers(self, languages: list[str] | None = None) -> bool:
        if not TREE_SITTER_AVAILABLE:
            return False
        from tree_sitter_language_pack import get_language, get_parser

        languages_to_load = languages or list(set(self.config["supported_languages"].values()))
        for lang in languages_to_load:
            try:
                if lang not in self.parsers:
                    self.languages[lang] = get_language(lang)
                    self.parsers[lang] = get_parser(lang)
            except Exception as e:
                logger.warning("Failed to load parser for %s: %s", lang, e)
        return len(self.parsers) > 0

    def analyze_source(
        self, source_code: str, language: str, file_path: str | None = None
    ) -> AnalysisResult:
        if language not in self.parsers:
            return AnalysisResult(success=False, error=f"Parser not available for '{language}'")
        try:
            parser = self.parsers[language]
            tree = parser.parse(bytes(source_code, "utf8"))
            root_node = tree.root_node
            semantic_info = self._extract_semantic_info(language, root_node)
            return AnalysisResult(
                success=not root_node.has_error,
                file_path=file_path,
                language=language,
                semantic_info=semantic_info,
                errors={"has_syntax_errors": root_node.has_error},
            )
        except Exception as e:
            return AnalysisResult(success=False, error=str(e), file_path=file_path)

    def _extract_semantic_info(self, language: str, root_node: Node) -> dict[str, Any]:
        info: defaultdict[str, Any] = defaultdict(list)

        query_string = """
            (function_definition name: (identifier) @function.name) @function.definition
            (class_definition name: (identifier) @class.name) @class.definition
            (call function: (identifier) @call.name) @call.expression
            (call function: (attribute attribute: (identifier) @call.name)) @call.expression
        """

        try:
            query = Query(self.languages[language], query_string)
            captures = query.captures(root_node)

            node_to_captures: dict[int, dict[str, Any]] = defaultdict(dict)
            for node, name in captures:
                node_to_captures[node.id][name] = node

            class_names = {
                parts["class.name"].text.decode("utf8")
                for parts in node_to_captures.values()
                if "class.definition" in parts and "class.name" in parts
            }

            for _node_id, captured_parts in node_to_captures.items():
                if "function.definition" in captured_parts and "function.name" in captured_parts:
                    info["definitions"].append(
                        {
                            "name": captured_parts["function.name"].text.decode("utf8"),
                            "type": "function",
                            "line": captured_parts["function.definition"].start_point[0] + 1,
                        }
                    )
                elif "class.definition" in captured_parts and "class.name" in captured_parts:
                    info["definitions"].append(
                        {
                            "name": captured_parts["class.name"].text.decode("utf8"),
                            "type": "class",
                            "line": captured_parts["class.definition"].start_point[0] + 1,
                        }
                    )
                elif "call.expression" in captured_parts and "call.name" in captured_parts:
                    call_name = captured_parts["call.name"].text.decode("utf8")
                    if call_name in class_names:
                        continue
                    call_node = captured_parts["call.expression"]
                    scope_name = self._find_scope_name(call_node)
                    info["calls"].append(
                        {
                            "name": call_name,
                            "type": "call",
                            "line": call_node.start_point[0] + 1,
                            "scope": scope_name,
                        }
                    )
        except Exception as e:
            logger.warning("Query failed in %s: %s. Falling back to manual extraction.", language, e)
            self._manual_extract(root_node, info)

        definitions = info.get("definitions", [])
        calls = info.get("calls", [])
        info["statistics"] = {
            "total_definitions": len(definitions),
            "total_calls": len(calls),
            "functions_count": len([d for d in definitions if d["type"] == "function"]),
            "classes_count": len([d for d in definitions if d["type"] == "class"]),
        }

        return dict(info)

    def _find_scope_name(self, node: Node) -> str:
        current = node.parent
        while current:
            if current.type in ["function_definition", "class_definition"]:
                name_node = current.child_by_field_name("name")
                if name_node:
                    return name_node.text.decode("utf8")
            current = current.parent
        return "global"

    def _manual_extract(self, node: Node, info: defaultdict):
        if node.type in ["function_definition", "class_definition"]:
            name_node = node.child_by_field_name("name")
            if name_node:
                info["definitions"].append(
                    {
                        "name": name_node.text.decode("utf8"),
                        "type": node.type,
                        "line": node.start_point[0] + 1,
                    }
                )
        elif node.type == "call":
            func_node = node.child_by_field_name("function")
            if func_node:
                name_node = (
                    func_node
                    if func_node.type == "identifier"
                    else func_node.child_by_field_name("attribute")
                )
                if name_node:
                    class_names = {
                        d["name"] for d in info["definitions"] if d.get("type") == "class"
                    }
                    call_name = name_node.text.decode("utf8")
                    if call_name not in class_names:
                        info["calls"].append(
                            {
                                "name": call_name,
                                "type": "call",
                                "line": node.start_point[0] + 1,
                                "scope": self._find_scope_name(node),
                            }
                        )
        for child in node.children:
            self._manual_extract(child, info)
