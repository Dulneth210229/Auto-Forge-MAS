"""
Security Agent prompt builder.

Builds the system prompt used by the LLM reviewer.
"""


class SecurityPromptBuilder:
    """
    Builds prompts for LLM-assisted security analysis.
    """

    @staticmethod
    def build_security_review_prompt(
        file_path: str,
        source_code: str,
    ) -> str:
        """
        Build a prompt for reviewing a source code file.

        Args:
            file_path: Relative path of the source file.
            source_code: Source code content.

        Returns:
            Prompt string.
        """

        return f"""
You are the Security Agent of the AutoForge multi-agent software development system.

Your responsibility is to review generated source code and identify security vulnerabilities.

Project Domain:
E-commerce web application.

Review the following source code and identify security issues such as:

- Hardcoded secrets
- SQL Injection
- Command Injection
- Cross-Site Scripting (XSS)
- Authentication issues
- Authorization issues
- Insecure file handling
- Unsafe deserialization
- Path traversal
- Weak cryptography
- Sensitive information exposure
- Missing input validation
- Dependency-related security concerns

Return ONLY valid JSON.

Do NOT include markdown.

Do NOT include explanations outside JSON.

Expected JSON format:

{{
  "findings": [
    {{
      "title": "",
      "description": "",
      "severity": "Critical | High | Medium | Low",
      "line": 0,
      "cwe": "",
      "recommendation": "",
      "confidence": 0.0
    }}
  ]
}}

If there are no security issues, return:

{{
  "findings": []
}}

File:

{file_path}

Source Code:

{source_code}
"""