# Security Report -- Finodil / Login and Signup

Generated: 2026-08-30T15:40:27.592056+00:00
Scan type: **AI model deep scan**
Gate decision: **REVIEW**
Total findings: 8 (0 critical, 7 moderate, 1 warning)

## Moderate

- **[MEDIUM]** `SEC-JS-006` (CWE-915) -- app\api\auth\login\route.ts:39 -- Dynamic bracket property access keyed directly by a request-controlled parameter name (e.g. obj[req.query.sort]) is an object-injection / prototype-pollution-adjacent pattern; the accessor should be validated against an explicit allow-list of field names.
  - Root cause: A dynamic bracket property access (obj[key]) was found at app\api\auth\login\route.ts:39, using a request-controlled value as the property name.
  - Suggested fix: Validate the property name against an explicit allow-list of known-safe field names before using it to index the object.
- **[HIGH]** `SEC-AI-DEEPSCAN` (CWE-89) -- app/api/auth/login/route.ts:31 -- NoSQL Injection -- The code allows user-controlled input to be used in the database query without proper validation, which can lead to NoSQL injection attacks.
  - Root cause: The `filter` object is directly used in the query without sanitization.
  - Suggested fix: Sanitize the `filter` object to only allow specific fields and values. Ensure that user input is properly validated and escaped.
- **[MEDIUM]** `SEC-AI-DEEPSCAN` (CWE-200) -- app/api/auth/login/route.ts:72 -- Sensitive Data Exposure -- The code returns sensitive user information in the API response, which can lead to sensitive data exposure.
  - Root cause: The response includes the user's `id`, `name`, and `email` fields.
  - Suggested fix: Remove sensitive fields from the response. Only return necessary information, such as a user ID or a token.
- **[MEDIUM]** `SEC-AI-DEEPSCAN` (CWE-307) -- app/api/auth/login/route.ts:50 -- Broken Authentication -- The code does not implement proper rate limiting or account lockout mechanisms, which can lead to brute force attacks.
  - Root cause: Lack of rate limiting or account lockout mechanisms.
  - Suggested fix: Implement rate limiting and account lockout mechanisms to prevent brute force attacks.
- **[MEDIUM]** `SEC-AI-DEEPSCAN` (CWE-88) -- app/api/auth/signup/route.ts:36 -- Security Misconfiguration -- The code does not implement proper input validation for the `password` field during signup, which can lead to weak password policies.
  - Root cause: Lack of strong password validation.
  - Suggested fix: Implement strong password validation, such as requiring special characters, numbers, and a minimum length.
- **[HIGH]** `SEC-AI-DEEPSCAN` (CWE-538) -- lib\api\loginAndSignup.ts:11 -- Password Exposure in API Response -- The signup and login functions return the response data directly, which may include sensitive information like passwords or tokens if not handled properly on the server side.
  - Root cause: Returning the response data directly without filtering out sensitive fields.
  - Suggested fix: Ensure that the server-side code does not return sensitive information like passwords or tokens in the response. Only return necessary data.
- **[MEDIUM]** `SEC-AI-DEEPSCAN` (CWE-798) -- lib\mongodb.ts:13 -- Hardcoded MongoDB URI -- The MongoDB URI is retrieved from the environment variable `MONGODB_URI`, but there is no check to ensure it is set. This could lead to a warning message and no database connection if the variable is unset.
  - Root cause: Lack of validation or error handling for the `MONGODB_URI` environment variable.
  - Suggested fix: Ensure that the `MONGODB_URI` environment variable is set and validated before attempting to connect to the database. Provide clear error messages if the variable is missing.

## Warning

- **[LOW]** `SEC-AI-DEEPSCAN` (CWE-798) -- app/api/auth/signup/route.ts:63 -- Hardcoded Secrets -- The code does not show any hardcoded secrets, but it is important to ensure that secrets are not hardcoded in the source code.
  - Root cause: No hardcoded secrets detected.
  - Suggested fix: Ensure that all secrets, such as API keys or database credentials, are stored securely and not hardcoded in the source code.

## Dependency scan

npm audit exit code: 0
Ran offline (sandbox has no outbound network to the npm advisory endpoint): True
Dependency summary: {'info': 0, 'low': 0, 'moderate': 0, 'high': 0, 'critical': 0, 'total': 0}

## LLM review layer

AI model deep scan ran over 3 batch(es) of real source code (3 succeeded, 0 failed): 7 finding(s).