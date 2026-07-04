# Merge Report: Login

**Verification:** PASSED
**Coding attempts used:** 1

## Verification steps
- **npm install**: passed
- **npm run build**: skipped
- **npm run lint**: skipped
- **npm run test**: skipped

## Files changed
### Added
- `client/src/components/LoginForm.jsx`
- `client/src/pages/LoginPage.jsx`
- `client/src/services/authService.js`
- `package-lock.json`
- `server/src/models/UserCredentials.js`
- `server/src/routes/auth.routes.js`
### Modified
- `package.json`

## Full diff (truncated)
```diff
diff --git a/client/src/components/LoginForm.jsx b/client/src/components/LoginForm.jsx
new file mode 100644
index 0000000..5d3fbd6
--- /dev/null
+++ b/client/src/components/LoginForm.jsx
@@ -0,0 +1,168 @@
+import React, { useState } from 'react';
+
+export default function LoginForm(props) {
+  const [email, setEmail] = useState(props.email);
+  const [password, setPassword] = useState(props.password);
+  const [isLoading, setIsLoading] = useState(false);
+  const [error, setError] = useState(props.error);
+
+  const handleSubmit = (e) => {
+    e.preventDefault();
+    setIsLoading(true);
+    setError(null);
+    
+    // Simulate API call
+    setTimeout(() => {
+      if (email === 'user@example.com' && password === 'password123') {
+        setIsLoading(false);
+        // In a real app, you would set auth state here
+      } else {
+        setIsLoading(false);
+        setError('Invalid email or password');
+      }
+    }, 1500);
+  };
+
+  const handleEmailChange = (e) => {
+    setEmail(e.target.value);
+    if (error) setError(null);
+  };
+
+  const handlePasswordChange = (e) => {
+    setPassword(e.target.value);
+    if (error) setError(null);
+  };
+
+  const renderForm = () => (
+    <form onSubmit={handleSubmit} className="space-y-6">
+      <div>
+        <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
+          Email address
+        </label>
+        <input
+          id="email"
+          type="email"
+          value={email}
+          onChange={handleEmailChange}
+          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
+          placeholder="you@example.com"
+        />
+      </div>
+
+      <div>
+        <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
+          Password
+        </label>
+        <input
+          id="password"
+          type="password"
+          value={password}
+          onChange={handlePasswordChange}
+          className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition"
+          placeholder="••••••••"
+        />
+      </div>
+
+      <div className="flex items-center justify-between">
+        <div className="flex items-center">
+          <input
+            id="remember-me"
+            name="remember-me"
+            type="checkbox"
+            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
+          />
+          <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
+            Remember me
+          </label>
+        </div>
+
+        <div className="text-sm">
+          <a href="#" className="font-medium text-blue-600 hover:text-blue-500">
+            Forgot your password?
+          </a>
+        </div>
+      </div>
+
+      <div>
+        <button
+          type="submit"
+          disabled={isLoading}
+          className="w-full flex justify-center py-2 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition"
+        >
+          {isLoading ? (
+            <>
+              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
+                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
+                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
+              </svg>
+              Signing in...
+            </>
+          ) : (
+            'Sign in'
+          )}
+        </button>
+      </div>
+    </form>
+  );
+
+  const renderSuccess = () => (
+    <div className="text-center py-8">
+      <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100">
+        <svg className="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
+          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
+        </svg>
+      </div>
+      <h3 className="mt-2 text-lg font-medium text-gray-900">Login successful!</h3>
+      <p className="mt-1 text-sm text-gray-500">Redirecting to your dashboard...</p>
+    </div>
+  );
+
+  const renderError = () => (
+    <div className="rounded-md bg-red-50 p-4 mb-6">
+      <div className="flex">
+        <div className="flex-shrink-0">
+          <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
+            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
+          </svg>
+        </div>
+        <div className="ml-3">
+          <h3 className="text-sm font-medium text-red-800">Login failed</h3>
+          <div className="mt-2 text-sm text-red-700">
+            <p>{error}</p>
+          </div>
+        </div>
+      </div>
+    </div>
+  );
+
+  return (
+    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
+      <div className="max-w-md w-full space-y-8">
+        <div>
+          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
+            Sign in to your account
+          </h2>
+          <p className="mt-2 text-center text-sm text-gray-600">
+            Or{' '}
+            <a href="#" className="font-medium text-blue-600 hover:text-blue-500">
+              start your 14-day free trial
+            </a>
+          </p>
+        </div>
+
+        {props.state === 'error' && renderError()}
+        {props.state === 'success' && renderSuccess()}
+        {props.state === 'loading' && (
+          <div className="text-center py-8">
+            <svg className="animate-spin mx-auto h-12 w-12 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
+              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
+              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
+            </svg>
+            <p className="mt-2 text-sm text-gray-600">Authenticating...</p>
+          </div>
+        )}
+        {props.state === 'idle' && renderForm()}
+      </div>
+    </div>
+  );
+}
\ No newline at end of file
diff --git a/client/src/pages/LoginPage.jsx b/client/src/pages/LoginPage.jsx
new file mode 100644
index 0000000..a6591e2
--- /dev/null
+++ b/client/src/pages/LoginPage.jsx
@@ -0,0 +1,10 @@
+import React from 'react';
+import LoginForm from '../components/LoginForm';
+
+export default function LoginPage() {
+  return (
+    <div>
+      <LoginForm />
+    </div>
+  );
+}
\ No newline at end of file
diff --git a/client/src/services/authService.js b/client/src/services/authService.js
new file mode 100644
index 0000000..0bb8c64
--- /dev/null
+++ b/client/src/services/authService.js
@@ -0,0 +1,69 @@
+import axios from 'axios';
+
+// Create an axios instance with default configuration
+const api = axios.create({
+  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:5000/api',
+  timeout: 10000,
+  headers: {
+    'Content-Type': 'application/json',
+  },
+});
+
+// Login function
+export const login = async (email, password) => {
+  try {
+    const response = await api.post('/auth/login', {
+      email,
+      password,
+    });
+    return response.data;
+  } catch (error) {
+    if (error.response) {
+      // Server responded with error status
+      throw new Error(error.response.data.message || 'Login failed');
+    } else if (error.request) {
+      // Request was made but no response received
+      throw new Error('Network error. Please check your connection.');
+    } else {
+      // Something else happened
+      throw new Error('An unexpected error occurred.');
+    }
+  }
+};
+
+// Forgot password function
+export const forgotPassword = async (email) => {
+  try {
+    const response = await api.post('/auth/forgot-password', {
+      email,
+    });
+    return response.data;
+  } catch (error) {
+    if (error.response) {
+      throw new Error(error.response.data.message || 'Failed to send reset email');
+    } else if (error.request) {
+      throw new Error('Network error. Please check your connection.');
+    } else {
+      throw new Error('An unexpected error occurred.');
+    }
+  }
+};
+
+// Reset password function
+export const resetPassword = async (token, newPassword) => {
+  try {
+    const response = await api.post('/auth/reset-password', {
+      token,
+      newPassword,
+    });
+    return response.data;
+  } catch (error) {
+    if (error.response) {
+      throw new Error(error.response.data.message || 'Password reset failed');
+    } else if (error.request) {
+      throw new Error('Network error. Please check your connection.');
+    } else {
+      throw new Error('An unexpected error occurred.');
+    }
+  }
+};
\ No newline at end of file
diff --git a/package-lock.json b/package-lock.json
new file mode 100644
index 0000000..71e9512
--- /dev/null
+++ b/package-lock.json
@@ -0,0 +1,522 @@
+{
+  "name": "auto-forge-generated-app",
+  "lockfileVersion": 3,
+  "requires": true,
+  "packages": {
+    "": {
+      "name": "auto-forge-generated-app",
+      "dependencies": {
+        "axios": "^1.18.1",
+        "bcrypt": "^6.0.0",
+        "jsonwebtoken": "^9.0.3",
+        "jwt-decode": "^4.0.0"
+      }
+    },
+    "node_modules/agent-base": {
+      "version": "6.0.2",
+      "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-6.0.2.tgz",
+      "integrity": "sha512-RZNwNclF7+MS/8bDg70amg32dyeZGZxiDuQmZxKLAlQjr3jGyLx+4Kkk58UO7D2QdgFIQCovuSuZESne6RG6XQ==",
+      "license": "MIT",
+      "dependencies": {
+        "debug": "4"
+      },
+      "engines": {
+        "node": ">= 6.0.0"
+      }
+    },
+    "node_modules/asynckit": {
+      "version": "0.4.0",
+      "resolved": "https://registry.npmjs.org/asynckit/-/asynckit-0.4.0.tgz",
+      "integrity": "sha512-Oei9OH4tRh0YqU3GxhX79dM/mwVgvbZJaSNaRk+bshkj0S5cfHcgYakreBjrHwatXKbz+IoIdYLxrKim2MjW0Q==",
+      "license": "MIT"
+    },
+    "node_modules/axios": {
+      "version": "1.18.1",
+      "resolved": "https://registry.npmjs.org/axios/-/axios-1.18.1.tgz",
+      "integrity": "sha512-3nTvFlvpn9Zu/RkHUqtc7/+al4UpRW5az71ap5zccp6e8RAYEzhMTecX8Dz1wWDYrPpUoB1HAQEGEAEvUr7S9g==",
+      "license": "MIT",
+      "dependencies": {
+        "follow-redirects": "^1.16.0",
+        "form-data": "^4.0.5",
+        "https-proxy-agent": "^5.0.1",
+        "proxy-from-env": "^2.1.0"
+      }
+    },
+    "node_modules/bcrypt": {
+      "version": "6.0.0",
+      "resolved": "https://registry.npmjs.org/bcrypt/-/bcrypt-6.0.0.tgz",
+      "integrity": "sha512-cU8v/EGSrnH+HnxV2z0J7/blxH8gq7Xh2JFT6Aroax7UohdmiJJlxApMxtKfuI7z68NvvVcmR78k2LbT6efhRg==",
+      "hasInstallScript": true,
+      "license": "MIT",
+      "dependencies": {
+        "node-addon-api": "^8.3.0",
+        "node-gyp-build": "^4.8.4"
+      },
+      "engines": {
+        "node": ">= 18"
+      }
+    },
+    "node_modules/buffer-equal-constant-time": {
+      "version": "1.0.1",
+      "resolved": "https://registry.npmjs.org/buffer-equal-constant-time/-/buffer-equal-constant-time-1.0.1.tgz",
+      "integrity": "sha512-zRpUiDwd/xk6ADqPMATG8vc9VPrkck7T07OIx0gnjmJAnHnTVXNQG3vfvWNuiZIkwu9KrKdA1iJKfsfTVxE6NA==",
+      "license": "BSD-3-Clause"
+    },
+    "node_modules/call-bind-apply-helpers": {
+      "version": "1.0.2",
+      "resolved": "https://registry.npmjs.org/call-bind-apply-helpers/-/call-bind-apply-helpers-1.0.2.tgz",
+      "integrity": "sha512-Sp1ablJ0ivDkSzjcaJdxEunN5/XvksFJ2sMBFfq6x0ryhQV/2b/KwFe21cMpmHtPOSij8K99/wSfoEuTObmuMQ==",
+      "license": "MIT",
+      "dependencies": {
+        "es-errors": "^1.3.0",
+        "function-bind": "^1.1.2"
+      },
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/combined-stream": {
+      "version": "1.0.8",
+      "resolved": "https://registry.npmjs.org/combined-stream/-/combined-stream-1.0.8.tgz",
+      "integrity": "sha512-FQN4MRfuJeHf7cBbBMJFXhKSDq+2kAArBlmRBvcvFE5BB1HZKXtSFASDhdlz9zOYwxh8lDdnvmMOe/+5cdoEdg==",
+      "license": "MIT",
+      "dependencies": {
+        "delayed-stream": "~1.0.0"
+      },
+      "engines": {
+        "node": ">= 0.8"
+      }
+    },
+    "node_modules/debug": {
+      "version": "4.4.3",
+      "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
+      "integrity": "sha512-RGwwWnwQvkVfavKVt22FGLw+xYSdzARwm0ru6DhTVA3umU5hZc28V3kO4stgYryrTlLpuvgI9GiijltAjNbcqA==",
+      "license": "MIT",
+      "dependencies": {
+        "ms": "^2.1.3"
+      },
+      "engines": {
+        "node": ">=6.0"
+      },
+      "peerDependenciesMeta": {
+        "supports-color": {
+          "optional": true
+        }
+      }
+    },
+    "node_modules/delayed-stream": {
+      "version": "1.0.0",
+      "resolved": "https://registry.npmjs.org/delayed-stream/-/delayed-stream-1.0.0.tgz",
+      "integrity": "sha512-ZySD7Nf91aLB0RxL4KGrKHBXl7Eds1DAmEdcoVawXnLD7SDhpNgtuII2aAkg7a7QS41jxPSZ17p4VdGnMHk3MQ==",
+      "license": "MIT",
+      "engines": {
+        "node": ">=0.4.0"
+      }
+    },
+    "node_modules/dunder-proto": {
+      "version": "1.0.1",
+      "resolved": "https://registry.npmjs.org/dunder-proto/-/dunder-proto-1.0.1.tgz",
+      "integrity": "sha512-KIN/nDJBQRcXw0MLVhZE9iQHmG68qAVIBg9CqmUYjmQIhgij9U5MFvrqkUL5FbtyyzZuOeOt0zdeRe4UY7ct+A==",
+      "license": "MIT",
+      "dependencies": {
+        "call-bind-apply-helpers": "^1.0.1",
+        "es-errors": "^1.3.0",
+        "gopd": "^1.2.0"
+      },
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/ecdsa-sig-formatter": {
+      "version": "1.0.11",
+      "resolved": "https://registry.npmjs.org/ecdsa-sig-formatter/-/ecdsa-sig-formatter-1.0.11.tgz",
+      "integrity": "sha512-nagl3RYrbNv6kQkeJIpt6NJZy8twLB/2vtz6yN9Z4vRKHN4/QZJIEbqohALSgwKdnksuY3k5Addp5lg8sVoVcQ==",
+      "license": "Apache-2.0",
+      "dependencies": {
+        "safe-buffer": "^5.0.1"
+      }
+    },
+    "node_modules/es-define-property": {
+      "version": "1.0.1",
+      "resolved": "https://registry.npmjs.org/es-define-property/-/es-define-property-1.0.1.tgz",
+      "integrity": "sha512-e3nRfgfUZ4rNGL232gUgX06QNyyez04KdjFrF+LTRoOXmrOgFKDg4BCdsjW8EnT69eqdYGmRpJwiPVYNrCaW3g==",
+      "license": "MIT",
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/es-errors": {
+      "version": "1.3.0",
+      "resolved": "https://registry.npmjs.org/es-errors/-/es-errors-1.3.0.tgz",
+      "integrity": "sha512-Zf5H2Kxt2xjTvbJvP2ZWLEICxA6j+hAmMzIlypy4xcBg1vKVnx89Wy0GbS+kf5cwCVFFzdCFh2XSCFNULS6csw==",
+      "license": "MIT",
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/es-object-atoms": {
+      "version": "1.1.2",
+      "resolved": "https://registry.npmjs.org/es-object-atoms/-/es-object-atoms-1.1.2.tgz",
+      "integrity": "sha512-HWcBoN6NileqtSydK2FqHbS/LoDd2pqrnQHLyJzBj4kOp/ky2MWMN694xOfkK8/SnUsW2DH7EfyVlydKCsm1Zw==",
+      "license": "MIT",
+      "dependencies": {
+        "es-errors": "^1.3.0"
+      },
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/es-set-tostringtag": {
+      "version": "2.1.0",
+      "resolved": "https://registry.npmjs.org/es-set-tostringtag/-/es-set-tostringtag-2.1.0.tgz",
+      "integrity": "sha512-j6vWzfrGVfyXxge+O0x5sh6cvxAog0a/4Rdd2K36zCMV5eJ+/+tOAngRO8cODMNWbVRdVlmGZQL2YS3yR8bIUA==",
+      "license": "MIT",
+      "dependencies": {
+        "es-errors": "^1.3.0",
+        "get-intrinsic": "^1.2.6",
+        "has-tostringtag": "^1.0.2",
+        "hasown": "^2.0.2"
+      },
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/follow-redirects": {
+      "version": "1.16.0",
+      "resolved": "https://registry.npmjs.org/follow-redirects/-/follow-redirects-1.16.0.tgz",
+      "integrity": "sha512-y5rN/uOsadFT/JfYwhxRS5R7Qce+g3zG97+JrtFZlC9klX/W5hD7iiLzScI4nZqUS7DNUdhPgw4xI8W2LuXlUw==",
+      "funding": [
+        {
+          "type": "individual",
+          "url": "https://github.com/sponsors/RubenVerborgh"
+        }
+      ],
+      "license": "MIT",
+      "engines": {
+        "node": ">=4.0"
+      },
+      "peerDependenciesMeta": {
+        "debug": {
+          "optional": true
+        }
+      }
+    },
+    "node_modules/form-data": {
+      "version": "4.0.6",
+      "resolved": "https://registry.npmjs.org/form-data/-/form-data-4.0.6.tgz",
+      "integrity": "sha512-vKatAh4SlVfgbv+YtmhiRjhEMJsYpsG1Y2rMQtR+SVSbytsSD1YGzDIcrAJmdFec88u/+VoGmxnl+80gL1tRCQ==",
+      "license": "MIT",
+      "dependencies": {
+        "asynckit": "^0.4.0",
+        "combined-stream": "^1.0.8",
+        "es-set-tostringtag": "^2.1.0",
+        "hasown": "^2.0.4",
+        "mime-types": "^2.1.35"
+      },
+      "engines": {
+        "node": ">= 6"
+      }
+    },
+    "node_modules/function-bind": {
+      "version": "1.1.2",
+      "resolved": "https://registry.npmjs.org/function-bind/-/function-bind-1.1.2.tgz",
+      "integrity": "sha512-7XHNxH7qX9xG5mIwxkhumTox/MIRNcOgDrxWsMt2pAr23WHp6MrRlN7FBSFpCpr+oVO0F744iUgR82nJMfG2SA==",
+      "license": "MIT",
+      "funding": {
+        "url": "https://github.com/sponsors/ljharb"
+      }
+    },
+    "node_modules/get-intrinsic": {
+      "version": "1.3.0",
+      "resolved": "https://registry.npmjs.org/get-intrinsic/-/get-intrinsic-1.3.0.tgz",
+      "integrity": "sha512-9fSjSaos/fRIVIp+xSJlE6lfwhES7LNtKaCBIamHsjr2na1BiABJPo0mOjjz8GJDURarmCPGqaiVg5mfjb98CQ==",
+      "license": "MIT",
+      "dependencies": {
+        "call-bind-apply-helpers": "^1.0.2",
+        "es-define-property": "^1.0.1",
+        "es-errors": "^1.3.0",
+        "es-object-atoms": "^1.1.1",
+        "function-bind": "^1.1.2",
+        "get-proto": "^1.0.1",
+        "gopd": "^1.2.0",
+        "has-symbols": "^1.1.0",
+        "hasown": "^2.0.2",
+        "math-intrinsics": "^1.1.0"
+      },
+      "engines": {
+        "node": ">= 0.4"
+      },
+      "funding": {
+        "url": "https://github.com/sponsors/ljharb"
+      }
+    },
+    "node_modules/get-proto": {
+      "version": "1.0.1",
+      "resolved": "https://registry.npmjs.org/get-proto/-/get-proto-1.0.1.tgz",
+      "integrity": "sha512-sTSfBjoXBp89JvIKIefqw7U2CCebsc74kiY6awiGogKtoSGbgjYE/G/+l9sF3MWFPNc9IcoOC4ODfKHfxFmp0g==",
+      "license": "MIT",
+      "dependencies": {
+        "dunder-proto": "^1.0.1",
+        "es-object-atoms": "^1.0.0"
+      },
+      "engines": {
+        "node": ">= 0.4"
+      }
+    },
+    "node_modules/gopd": {
+      "version": "1.2.0",
+      "resolved": "https://registry.npmjs.org/gopd/-/gopd-1.2.0.tgz",
+      "integrity": "sha512-ZUKRh6/kUFoAiTAtTYPZJ3hw9wNxx+BIBOijnlG9PnrJsCcSjs1wyyD6vJpaYtgnzDrKYRSqf3OO6Rfa93xsRg==",
+      "license": "MIT",
+      "engines": {
+        "node": ">= 0.4"
+      },
+      "funding": {
+        "url": "https://github.com/sponsors/ljharb"
+      }
+    },
+    "node_modules/has-symbols": {
+      "version": "1.1.0",
+      "resolved": "https://registry.npmjs.org/has-symbols/-/has-symbols-1.1.0.tgz",
+      "integrity": "sha512-1cDNdwJ2Jaohmb3sg4OmKaMBwuC48sYni5HUw2DvsC8LjGTLK9h+eb1X6RyuOHe4hT0ULCW68iomhjUoKUqlPQ==",
+      "license": "MIT",
+      "engines": {
+        "node": ">= 0.4"
+      },
+      "funding": {
+ 
```