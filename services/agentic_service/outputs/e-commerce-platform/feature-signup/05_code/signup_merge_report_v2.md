# Merge Report: Signup

**Verification:** PASSED
**Coding attempts used:** 1

## Verification steps
- **npm install (server)**: passed
- **npm install (client)**: passed
- **server boot (curl /api/health)**: passed
- **client build (vite build)**: passed
- **npm run lint (root)**: skipped
- **npm run test (root)**: skipped
- **endpoint route coverage**: passed
- **placeholder-stub scan**: info
  ```
  Found possible placeholder/stub logic (does not fail verification, review before approving):
  - server/src/routes/auth.routes.js:100: // In a real app, you would generate a reset token and send an email
  - server/src/routes/auth.routes.js:114: // In a real app, you would verify the reset token
  - server/src/routes/auth.routes.js:120: // In a real app, you would update the user's password
  ```

## Files changed
### Modified
- `package-lock.json`
- `package.json`
- `server/package-lock.json`
- `server/src/models/UserCredentials.js`
- `server/src/routes/auth.routes.js`

## Full diff (truncated)
```diff
diff --git a/package-lock.json b/package-lock.json
index 71e9512..ebbcfc5 100644
--- a/package-lock.json
+++ b/package-lock.json
@@ -8,8 +8,22 @@
       "dependencies": {
         "axios": "^1.18.1",
         "bcrypt": "^6.0.0",
+        "bcryptjs": "^3.0.3",
         "jsonwebtoken": "^9.0.3",
         "jwt-decode": "^4.0.0"
+      },
+      "devDependencies": {
+        "concurrently": "^8.2.2"
+      }
+    },
+    "node_modules/@babel/runtime": {
+      "version": "7.29.7",
+      "resolved": "https://registry.npmjs.org/@babel/runtime/-/runtime-7.29.7.tgz",
+      "integrity": "sha512-Nq8OhGWiZIZGV6hLHoyAKLLcJihP/xFeBMGJoUrxTX2psI8dCifzLhZISFb+VWS3wFMRDmCGw5R+dOySCqPLhw==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">=6.9.0"
       }
     },
     "node_modules/agent-base": {
@@ -24,6 +38,32 @@
         "node": ">= 6.0.0"
       }
     },
+    "node_modules/ansi-regex": {
+      "version": "5.0.1",
+      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-5.0.1.tgz",
+      "integrity": "sha512-quJQXlTSUGL2LH9SUXo8VwsY4soanhgo6LNSm84E1LBcE8s3O0wpdiRzyR9z/ZZJMlMWv37qOOb9pdJlMUEKFQ==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">=8"
+      }
+    },
+    "node_modules/ansi-styles": {
+      "version": "4.3.0",
+      "resolved": "https://registry.npmjs.org/ansi-styles/-/ansi-styles-4.3.0.tgz",
+      "integrity": "sha512-zbB9rCJAT1rbjiVDb2hqKFHNYLxgtk8NURxZ3IZwD3F6NtxbXZQCnnSi1Lkx+IDohdPlFp222wVALIheZJQSEg==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "color-convert": "^2.0.1"
+      },
+      "engines": {
+        "node": ">=8"
+      },
+      "funding": {
+        "url": "https://github.com/chalk/ansi-styles?sponsor=1"
+      }
+    },
     "node_modules/asynckit": {
       "version": "0.4.0",
       "resolved": "https://registry.npmjs.org/asynckit/-/asynckit-0.4.0.tgz",
@@ -56,6 +96,15 @@
         "node": ">= 18"
       }
     },
+    "node_modules/bcryptjs": {
+      "version": "3.0.3",
+      "resolved": "https://registry.npmjs.org/bcryptjs/-/bcryptjs-3.0.3.tgz",
+      "integrity": "sha512-GlF5wPWnSa/X5LKM1o0wz0suXIINz1iHRLvTS+sLyi7XPbe5ycmYI3DlZqVGZZtDgl4DmasFg7gOB3JYbphV5g==",
+      "license": "BSD-3-Clause",
+      "bin": {
+        "bcrypt": "bin/bcrypt"
+      }
+    },
     "node_modules/buffer-equal-constant-time": {
       "version": "1.0.1",
       "resolved": "https://registry.npmjs.org/buffer-equal-constant-time/-/buffer-equal-constant-time-1.0.1.tgz",
@@ -75,6 +124,71 @@
         "node": ">= 0.4"
       }
     },
+    "node_modules/chalk": {
+      "version": "4.1.2",
+      "resolved": "https://registry.npmjs.org/chalk/-/chalk-4.1.2.tgz",
+      "integrity": "sha512-oKnbhFyRIXpUuez8iBMmyEa4nbj4IOQyuhc/wy9kY7/WVPcwIO9VA668Pu8RkO7+0G76SLROeyw9CpQ061i4mA==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "ansi-styles": "^4.1.0",
+        "supports-color": "^7.1.0"
+      },
+      "engines": {
+        "node": ">=10"
+      },
+      "funding": {
+        "url": "https://github.com/chalk/chalk?sponsor=1"
+      }
+    },
+    "node_modules/chalk/node_modules/supports-color": {
+      "version": "7.2.0",
+      "resolved": "https://registry.npmjs.org/supports-color/-/supports-color-7.2.0.tgz",
+      "integrity": "sha512-qpCAvRl9stuOHveKsn7HncJRvv501qIacKzQlO/+Lwxc9+0q2wLyv4Dfvt80/DPn2pqOBsJdDiogXGR9+OvwRw==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "has-flag": "^4.0.0"
+      },
+      "engines": {
+        "node": ">=8"
+      }
+    },
+    "node_modules/cliui": {
+      "version": "8.0.1",
+      "resolved": "https://registry.npmjs.org/cliui/-/cliui-8.0.1.tgz",
+      "integrity": "sha512-BSeNnyus75C4//NQ9gQt1/csTXyo/8Sb+afLAkzAptFuMsod9HFokGNudZpi/oQV73hnVK+sR+5PVRMd+Dr7YQ==",
+      "dev": true,
+      "license": "ISC",
+      "dependencies": {
+        "string-width": "^4.2.0",
+        "strip-ansi": "^6.0.1",
+        "wrap-ansi": "^7.0.0"
+      },
+      "engines": {
+        "node": ">=12"
+      }
+    },
+    "node_modules/color-convert": {
+      "version": "2.0.1",
+      "resolved": "https://registry.npmjs.org/color-convert/-/color-convert-2.0.1.tgz",
+      "integrity": "sha512-RRECPsj7iu/xb5oKYcsFHSppFNnsj/52OVTRKb4zP5onXwVF3zVmmToNcOfGC+CRDpfK/U584fMg38ZHCaElKQ==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "color-name": "~1.1.4"
+      },
+      "engines": {
+        "node": ">=7.0.0"
+      }
+    },
+    "node_modules/color-name": {
+      "version": "1.1.4",
+      "resolved": "https://registry.npmjs.org/color-name/-/color-name-1.1.4.tgz",
+      "integrity": "sha512-dOy+3AuW3a2wNbZHIuMZpTcgjGuLU/uBL/ubcZF9OXbDo8ff4O8yVp5Bf0efS8uEoYo5q4Fx7dY9OgQGXgAsQA==",
+      "dev": true,
+      "license": "MIT"
+    },
     "node_modules/combined-stream": {
       "version": "1.0.8",
       "resolved": "https://registry.npmjs.org/combined-stream/-/combined-stream-1.0.8.tgz",
@@ -87,6 +201,51 @@
         "node": ">= 0.8"
       }
     },
+    "node_modules/concurrently": {
+      "version": "8.2.2",
+      "resolved": "https://registry.npmjs.org/concurrently/-/concurrently-8.2.2.tgz",
+      "integrity": "sha512-1dP4gpXFhei8IOtlXRE/T/4H88ElHgTiUzh71YUmtjTEHMSRS2Z/fgOxHSxxusGHogsRfxNq1vyAwxSC+EVyDg==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "chalk": "^4.1.2",
+        "date-fns": "^2.30.0",
+        "lodash": "^4.17.21",
+        "rxjs": "^7.8.1",
+        "shell-quote": "^1.8.1",
+        "spawn-command": "0.0.2",
+        "supports-color": "^8.1.1",
+        "tree-kill": "^1.2.2",
+        "yargs": "^17.7.2"
+      },
+      "bin": {
+        "conc": "dist/bin/concurrently.js",
+        "concurrently": "dist/bin/concurrently.js"
+      },
+      "engines": {
+        "node": "^14.13.0 || >=16.0.0"
+      },
+      "funding": {
+        "url": "https://github.com/open-cli-tools/concurrently?sponsor=1"
+      }
+    },
+    "node_modules/date-fns": {
+      "version": "2.30.0",
+      "resolved": "https://registry.npmjs.org/date-fns/-/date-fns-2.30.0.tgz",
+      "integrity": "sha512-fnULvOpxnC5/Vg3NCiWelDsLiUc9bRwAPs/+LfTLNvetFCtCTN+yQz15C/fs4AwX1R9K5GLtLfn8QW+dWisaAw==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "@babel/runtime": "^7.21.0"
+      },
+      "engines": {
+        "node": ">=0.11"
+      },
+      "funding": {
+        "type": "opencollective",
+        "url": "https://opencollective.com/date-fns"
+      }
+    },
     "node_modules/debug": {
       "version": "4.4.3",
       "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
@@ -136,6 +295,13 @@
         "safe-buffer": "^5.0.1"
       }
     },
+    "node_modules/emoji-regex": {
+      "version": "8.0.0",
+      "resolved": "https://registry.npmjs.org/emoji-regex/-/emoji-regex-8.0.0.tgz",
+      "integrity": "sha512-MSjYzcWNOA0ewAHpz0MxpYFvwg6yjy1NG3xteoqz644VCo/RPgnr1/GGt+ic3iJTzQ8Eu3TdM14SawnVUmGE6A==",
+      "dev": true,
+      "license": "MIT"
+    },
     "node_modules/es-define-property": {
       "version": "1.0.1",
       "resolved": "https://registry.npmjs.org/es-define-property/-/es-define-property-1.0.1.tgz",
@@ -181,6 +347,16 @@
         "node": ">= 0.4"
       }
     },
+    "node_modules/escalade": {
+      "version": "3.2.0",
+      "resolved": "https://registry.npmjs.org/escalade/-/escalade-3.2.0.tgz",
+      "integrity": "sha512-WUj2qlxaQtO4g6Pq5c29GTcWGDyd8itL8zTlipgECz3JesAiiOKotd8JU6otB3PACgG6xkJUyVhboMS+bje/jA==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">=6"
+      }
+    },
     "node_modules/follow-redirects": {
       "version": "1.16.0",
       "resolved": "https://registry.npmjs.org/follow-redirects/-/follow-redirects-1.16.0.tgz",
@@ -226,6 +402,16 @@
         "url": "https://github.com/sponsors/ljharb"
       }
     },
+    "node_modules/get-caller-file": {
+      "version": "2.0.5",
+      "resolved": "https://registry.npmjs.org/get-caller-file/-/get-caller-file-2.0.5.tgz",
+      "integrity": "sha512-DyFP3BM/3YHTQOCUL/w0OZHR0lpKeGrxotcHWcqNEdnltqFwXVfhEBQ94eIo34AfQpo0rGki4cyIiftY06h2Fg==",
+      "dev": true,
+      "license": "ISC",
+      "engines": {
+        "node": "6.* || 8.* || >= 10.*"
+      }
+    },
     "node_modules/get-intrinsic": {
       "version": "1.3.0",
       "resolved": "https://registry.npmjs.org/get-intrinsic/-/get-intrinsic-1.3.0.tgz",
@@ -275,6 +461,16 @@
         "url": "https://github.com/sponsors/ljharb"
       }
     },
+    "node_modules/has-flag": {
+      "version": "4.0.0",
+      "resolved": "https://registry.npmjs.org/has-flag/-/has-flag-4.0.0.tgz",
+      "integrity": "sha512-EykJT/Q1KjTWctppgIAgfSO0tKVuZUjhgMr17kqTumMl6Afv3EISleU7qZUzoXDFTAHTDC4NOoG/ZxU3EvlMPQ==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">=8"
+      }
+    },
     "node_modules/has-symbols": {
       "version": "1.1.0",
       "resolved": "https://registry.npmjs.org/has-symbols/-/has-symbols-1.1.0.tgz",
@@ -327,6 +523,16 @@
         "node": ">= 6"
       }
     },
+    "node_modules/is-fullwidth-code-point": {
+      "version": "3.0.0",
+      "resolved": "https://registry.npmjs.org/is-fullwidth-code-point/-/is-fullwidth-code-point-3.0.0.tgz",
+      "integrity": "sha512-zymm5+u+sCsSWyD9qNaejV3DFvhCKclKdizYaJUuHA83RLjb7nSuGnddCHGv0hk+KY7BMAlsWeK4Ueg6EV6XQg==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">=8"
+      }
+    },
     "node_modules/jsonwebtoken": {
       "version": "9.0.3",
       "resolved": "https://registry.npmjs.org/jsonwebtoken/-/jsonwebtoken-9.0.3.tgz",
@@ -379,6 +585,13 @@
         "node": ">=18"
       }
     },
+    "node_modules/lodash": {
+      "version": "4.18.1",
+      "resolved": "https://registry.npmjs.org/lodash/-/lodash-4.18.1.tgz",
+      "integrity": "sha512-dMInicTPVE8d1e5otfwmmjlxkZoUpiVLwyeTdUsi/Caj/gfzzblBcCE5sRHV/AsjuCmxWrte2TNGSYuCeCq+0Q==",
+      "dev": true,
+      "license": "MIT"
+    },
     "node_modules/lodash.includes": {
       "version": "4.3.0",
       "resolved": "https://registry.npmjs.org/lodash.includes/-/lodash.includes-4.3.0.tgz",
@@ -486,6 +699,26 @@
         "node": ">=10"
       }
     },
+    "node_modules/require-directory": {
+      "version": "2.1.1",
+      "resolved": "https://registry.npmjs.org/require-directory/-/require-directory-2.1.1.tgz",
+      "integrity": "sha512-fGxEI7+wsG9xrvdjsrlmL22OMTTiHRwAMroiEeMgq8gzoLC/PQr7RsRDSTLUg/bZAZtF+TVIkHc6/4RIKrui+Q==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">=0.10.0"
+      }
+    },
+    "node_modules/rxjs": {
+      "version": "7.8.2",
+      "resolved": "https://registry.npmjs.org/rxjs/-/rxjs-7.8.2.tgz",
+      "integrity": "sha512-dhKf903U/PQZY6boNNtAGdWbG85WAbjT/1xYoZIC7FAY0yWapOBQVsVrDl58W86//e1VpMNBtRV4MaXfdMySFA==",
+      "dev": true,
+      "license": "Apache-2.0",
+      "dependencies": {
+        "tslib": "^2.1.0"
+      }
+    },
     "node_modules/safe-buffer": {
       "version": "5.2.1",
       "resolved": "https://registry.npmjs.org/safe-buffer/-/safe-buffer-5.2.1.tgz",
@@ -517,6 +750,143 @@
       "engines": {
         "node": ">=10"
       }
+    },
+    "node_modules/shell-quote": {
+      "version": "1.9.0",
+      "resolved": "https://registry.npmjs.org/shell-quote/-/shell-quote-1.9.0.tgz",
+      "integrity": "sha512-Iov+JwFv/2HcTpcwNMKd8+IWNb8tboQJNQTkAY/LLVK7gGH9jy+LGkVqPxfekHl+yMmiqXszdGWXgkfml7hjqA==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": ">= 0.4"
+      },
+      "funding": {
+        "url": "https://github.com/sponsors/ljharb"
+      }
+    },
+    "node_modules/spawn-command": {
+      "version": "0.0.2",
+      "resolved": "https://registry.npmjs.org/spawn-command/-/spawn-command-0.0.2.tgz",
+      "integrity": "sha512-zC8zGoGkmc8J9ndvml8Xksr1Amk9qBujgbF0JAIWO7kXr43w0h/0GJNM/Vustixu+YE8N/MTrQ7N31FvHUACxQ==",
+      "dev": true
+    },
+    "node_modules/string-width": {
+      "version": "4.2.3",
+      "resolved": "https://registry.npmjs.org/string-width/-/string-width-4.2.3.tgz",
+      "integrity": "sha512-wKyQRQpjJ0sIp62ErSZdGsjMJWsap5oRNihHhu6G7JVO/9jIB6UyevL+tXuOqrng8j/cxKTWyWUwvSTriiZz/g==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "emoji-regex": "^8.0.0",
+        "is-fullwidth-code-point": "^3.0.0",
+        "strip-ansi": "^6.0.1"
+      },
+      "engines": {
+        "node": ">=8"
+      }
+    },
+    "node_modules/strip-ansi": {
+      "version": "6.0.1",
+      "resolved": "https://registry.npmjs.org/strip-ansi/-/strip-ansi-6.0.1.tgz",
+      "integrity": "sha512-Y38VPSHcqkFrCpFnQ9vuSXmquuv5oXOKpGeT6aGrr3o3Gc9AlVa6JBfUSOCnbxGGZF+/0ooI7KrPuUSztUdU5A==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "ansi-regex": "^5.0.1"
+      },
+      "engines": {
+        "node": ">=8"
+      }
+    },
+    "node_modules/supports-color": {
+      "version": "8.1.1",
+      "resolved": "https://registry.npmjs.org/supports-color/-/supports-color-8.1.1.tgz",
+      "integrity": "sha512-MpUEN2OodtUzxvKQl72cUF7RQ5EiHsGvSsVG0ia9c5RbWGL2CI4C7EpPS8UTBIplnlzZiNuV56w+FuNxy3ty2Q==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "has-flag": "^4.0.0"
+      },
+      "engines": {
+        "node": ">=10"
+      },
+      "funding": {
+        "url": "https://github.com/chalk/supports-color?sponsor=1"
+      }
+    },
+    "node_modules/tree-kill": {
+      "version": "1.2.2",
+      "resolved": "https://registry.npmjs.org/tree-kill/-/tree-kill-1.2.2.tgz",
+      "integrity": "sha512-L0Orpi8qGpRG//Nd+H90vFB+3iHnue1zSSGmNOOCh1GLJ7rUKVwV2HvijphGQS2UmhUZewS9VgvxYIdgr+fG1A==",
+      "dev": true,
+      "license": "MIT",
+      "bin": {
+        "tree-kill": "cli.js"
+      }
+    },
+    "node_modules/tslib": {
+      "version": "2.8.1",
+      "resolved": "https://registry.npmjs.org/tslib/-/tslib-2.8.1.tgz",
+      "integrity": "sha512-oJFu94HQb+KVduSUQL7wnpmqnfmLsOA/nAh6b6EH0wCEoK0/mPeXU6c3wKDV83MkOuHPRHtSXKKU99IBazS/2w==",
+      "dev": true,
+      "license": "0BSD"
+    },
+    "node_modules/wrap-ansi": {
+      "version": "7.0.0",
+      "resolved": "https://registry.npmjs.org/wrap-ansi/-/wrap-ansi-7.0.0.tgz",
+      "integrity": "sha512-YVGIj2kamLSTxw6NsZjoBxfSwsn0ycdesmc4p+Q21c5zPuZ1pl+NfxVdxPtdHvmNVOQ6XSYG4AUtyt/Fi7D16Q==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "ansi-styles": "^4.0.0",
+        "string-width": "^4.1.0",
+        "strip-ansi": "^6.0.0"
+      },
+      "engines": {
+        "node": ">=10"
+      },
+      "funding": {
+        "url": "https://github.com/chalk/wrap-ansi?sponsor=1"
+      }
+    },
+    "node_modules/y18n": {
+      "version": "5.0.8",
+      "resolved": "https://registry.npmjs.org/y18n/-/y18n-5.0.8.tgz",
+      "integrity": "sha512-0pfFzegeDWJHJIAmTLRP2DwHjdF5s7jo9tuztdQxAhINCdvS+3nGINqPd00AphqJR/0LhANUS6/+7SCb98YOfA==",
+      "dev": true,
+      "license": "ISC",
+      "engines": {
+        "node": ">=10"
+      }
+    },
+    "node_modules/yargs": {
+      "version": "17.7.3",
+      "resolved": "https://registry.npmjs.org/yargs/-/yargs-17.7.3.tgz",
+      "integrity": "sha512-GZtjxm/J/4TSxuL3FNYjCmLktBTnIw/rVmKSIyKeYAZpmJB2ig9VauCC5xsa82GNKVKDAqpOn3KVzNt0zmrU0g==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "cliui": "^8.0.1",
+        "escalade": "^3.1.1",
+        "get-caller-file": "^2.0.5",
+        "require-directory": "^2.1.1",
+        "string-width": "^4.2.3",
+        "y18n": "^5.0.5",
+        "yargs-parser": "^21.1.1"
+      },
+      "engines": {
+        "node": ">=12"
+      }
+    },
+    "node_modules/yargs-parser": {
+      "version": "21.1.1",
+      "resolved": "https://registry.npmjs.org/yargs-parser/-/yargs-parser-21.1.1.tgz",
+      "integrity": "sha512-tVpsJW7DdjecAiFpbIB1e3qxIQsE6NoPc5/eTdrbbIC4h0LVsWhnoa3g+m2HclBIujHzsxZ4VJVA+GUuc2/LBw==",
+      "dev": true,
+      "license": "ISC",
+      "engines": {
+        "node": ">=12"
+      }
     }
   }
 }
diff --git a/package.json b/package.json
index 78f9702..e85e411 100644
--- a/package.json
+++ b/package.json
@@ -4,6 +4,7 @@
   "dependencies": {
     "axios": "^1.18.1",
     "bcrypt": "^6.0.0",
+    "bcryptjs": "^3.0.3",
     "jsonwebtoken": "^9.0.3",
     "jwt-decode": "^4.0.0"
   },
diff --git a/server/package-lock.json b/server/package-lock.json
index 6372d3b..43ed07f 100644
--- a/server/package-lock.json
+++ b/server/package-lock.json
@@ -10,6 +10,8 @@
         "cors": "^2.8.5",
         "dotenv": "^16.4.5",
         "express": "^4.19.2",
+        "express-rate-limit": "^7.4.0",
+        "helmet": "^7.1.0",
         "jsonwebtoken": "^9.0.3",
         "mongoose": "^8.5.0"
       },
@@ -461,6 +463,21 @@
         "url": "https://opencollective.com/express"
       }
     },
+    "node_modules/express-rate-limit": {
+      "version": "7.5.1",
+      "resolved": "https://registry.npmjs.org/express-rate-limit/-/express-rate-limit-7.5.1.tgz",
+      "integrity": "sha512-7iN8iPMDzOMHPUYllBEsQdWVB6fPDMPqwjBaFrgr4Jgr/+okjvzAy+UHlYYL/Vs0OsOrMkwS6PJDkFlJwoxUnw==",
+      "license": "MIT",
+      "engines": {
+        "node": ">= 16"
+      },
+      "funding": {
+        "url": "https://github.com/sponsors/express-rate-limit"
+      },
+      "peerDependencies": {
+        "express": ">= 4.11"
+      }
+    },
     "node_modules/fill-range": {
       "version": "7.1.1",
       "resolved": "https://registry.npmjs.org/fill-range/-/fill-range-7.1.1.tgz",
@@ -630,6 +647,15 @@
         "node": ">= 0.4"
       }
     },
+    "node_modules/helmet": {
+      "version": "7.2.0",
+      "resolved": "https://registry.npmjs.org/helmet/-/helmet-7.2.0.tgz",
+      "integrity": "sha512-ZRiwvN089JfMXokizgqEPXsl2Guk094yExfoDXR0cBYWxtBbaSww/w+vT4WEJsBW2iTUi1GgZ6swmoug3Oy4Xw==",
+      "license": "MIT",
+      "engines": {
+        "node": ">=16.0.0"
+      }
+    },
     "node_modules/http-errors": {
       "version": "2.0.1",
       "resolved": "https://registry.npmjs.org/http-errors/-/http-errors-2.0.1.tgz",
diff --git a/server/src/models/UserCredentials.js b/server/src/models/UserCredentials.js
index 7a4c14d..41e6358 100644
--- a/server/src/models/UserCredentials.js
+++ b/server/src/models/UserCredentials.js
@@ -15,6 +15,11 @@ const userCredentialsSchema = new mongoose.Schema({
     required: true,
     minlength: 6
   },
+  fullName: {
+    type: String,
+    required: true,
+    trim: true
+  },
   createdAt: {
     type: Date,
     default: Date.now
diff --git a/server/src/routes/auth.routes.js b/server/src/routes/auth.routes.js
index 80de1fc..78f1f1f 100644
--- a/server/src/routes/auth.routes.js
+++ b/server/src/routes/auth.routes.js
@@ -42,6 +42,49 @@ router.post('/login', async (req, res) => {
   }
 });
 
+// Signup route
+router.post('/signup', async (req, res) => {
+  try {
+    const { email, password, fullName } = req.body;
+
+    // Validate input
+    if (!email || !password || !fullName) {
+      return res.status(400).json({ message: 'Email, password, and full name are required' });
+    }
+
+    // Check if user already exists
+    const existingUser = await UserCredentials.findOne({ email });
+    if (existingUser) {
+      return res.status(400).json({ message: 'User with this email already exists' });
+    }
+
+    // Create new user
+    const user = new UserCredentials({
+      email,
+      password,
+      fullName
+    });
+
+    await user.save();
+
+    // Generate token
+    const token = generateToken(user._id);
+
+    res.status(201).json({
+      message: 'Signup successful',
+      token,
+      user: {
+        id: user._id,
+        email: user.email,
+        fullName: user.fullName
+      }
+    });
+  } catch (error) {
+    console.error('Signup error:', error);
+    res.status(500).json({ message: 'Internal server error' }
```