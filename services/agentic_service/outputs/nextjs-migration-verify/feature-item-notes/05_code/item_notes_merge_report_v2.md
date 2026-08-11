# Merge Report: Item Notes

**Verification:** PASSED
**Coding attempts used:** 1

## Verification steps
- **next.config.mjs integrity**: passed
- **npm install**: passed
- **next build**: passed
- **server boot (next start + /api/health)**: passed
- **npm run test (root)**: skipped
- **endpoint route coverage**: passed
- **page reachability**: passed
- **home page render**: passed
- **feature page render**: info
  ```
  All 1 feature page(s) rendered cleanly:
  - /item-notes: /item-notes responded with HTTP 200 and no JS errors.
  ```
- **placeholder-stub scan**: info
  ```
  Found possible placeholder/stub logic (does not fail verification, review before approving):
  - app/item-notes/page.tsx:12: const [itemId] = useState("example-item-id"); // This would come from the URL in a real app
  ```

## Files changed
### Added
- `app/api/item-notes/route.ts`
- `app/item-notes/page.tsx`
- `components/Footer.css`
- `components/Footer.tsx`
- `components/ItemNotesList.jsx`
- `components/Navbar.css`
- `components/Navbar.tsx`
- `components/NoteInputField.jsx`
- `lib/api/itemNotes.ts`
- `models/ItemNote.ts`
- `next.config.mjs`
- `package-lock.json`
### Modified
- `app/layout.tsx`
- `app/page.tsx`
### Deleted
- `next.config.ts`

## Full diff (truncated)
```diff
diff --git a/app/api/item-notes/route.ts b/app/api/item-notes/route.ts
new file mode 100644
index 0000000..429b385
--- /dev/null
+++ b/app/api/item-notes/route.ts
@@ -0,0 +1,68 @@
+import { NextResponse } from "next/server";
+import { connectToDatabase } from "@/lib/mongodb";
+import ItemNote from "@/models/ItemNote";
+
+export const dynamic = "force-dynamic";
+
+export async function GET(request: Request) {
+  const { searchParams } = new URL(request.url);
+  const itemId = searchParams.get("itemId");
+
+  if (!itemId) {
+    return NextResponse.json(
+      { error: "itemId query parameter is required" },
+      { status: 400 }
+    );
+  }
+
+  try {
+    await connectToDatabase();
+    const notes = await ItemNote.find({ itemId })
+      .sort({ createdAt: -1 })
+      .lean();
+
+    return NextResponse.json(notes);
+  } catch (error) {
+    console.error("Error fetching item notes:", error);
+    return NextResponse.json(
+      { error: "Failed to fetch item notes" },
+      { status: 500 }
+    );
+  }
+}
+
+export async function POST(request: Request) {
+  const { itemId, content, authorId } = await request.json();
+
+  if (!itemId || !content || !authorId) {
+    return NextResponse.json(
+      { error: "itemId, content, and authorId are required" },
+      { status: 400 }
+    );
+  }
+
+  if (content.length > 500) {
+    return NextResponse.json(
+      { error: "Content must be 500 characters or less" },
+      { status: 400 }
+    );
+  }
+
+  try {
+    await connectToDatabase();
+    const newNote = new ItemNote({
+      itemId,
+      content,
+      authorId
+    });
+    await newNote.save();
+
+    return NextResponse.json(newNote, { status: 201 });
+  } catch (error) {
+    console.error("Error creating item note:", error);
+    return NextResponse.json(
+      { error: "Failed to create item note" },
+      { status: 500 }
+    );
+  }
+}
\ No newline at end of file
diff --git a/app/item-notes/page.tsx b/app/item-notes/page.tsx
new file mode 100644
index 0000000..bd17921
--- /dev/null
+++ b/app/item-notes/page.tsx
@@ -0,0 +1,70 @@
+"use client";
+
+import { useState, useEffect } from "react";
+import { listItemNotes, createItemNote } from "@/lib/api/itemNotes";
+import ItemNotesList from "@/components/ItemNotesList";
+import NoteInputField from "@/components/NoteInputField";
+
+export default function ItemNotesPage() {
+  const [notes, setNotes] = useState<any[]>([]);
+  const [loading, setLoading] = useState(true);
+  const [error, setError] = useState<string | null>(null);
+  const [itemId] = useState("example-item-id"); // This would come from the URL in a real app
+
+  const fetchNotes = async () => {
+    try {
+      setLoading(true);
+      const data = await listItemNotes(itemId);
+      setNotes(data);
+      setError(null);
+    } catch (err) {
+      setError(err instanceof Error ? err.message : String(err));
+    } finally {
+      setLoading(false);
+    }
+  };
+
+  const handleCreateNote = async (content: string) => {
+    try {
+      const newNote = await createItemNote(itemId, content);
+      setNotes(prev => [newNote, ...prev]);
+    } catch (err) {
+      setError(err instanceof Error ? err.message : String(err));
+    }
+  };
+
+  useEffect(() => {
+    fetchNotes();
+  }, []);
+
+  if (loading) {
+    return <div className="flex justify-center items-center h-screen">Loading...</div>;
+  }
+
+  if (error) {
+    return <div className="flex justify-center items-center h-screen text-red-500">Error: {error}</div>;
+  }
+
+  return (
+    <div className="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
+      <div className="max-w-3xl mx-auto">
+        <h1 className="text-3xl font-bold text-center text-gray-900 mb-8">Item Notes</h1>
+        
+        <div className="mb-8">
+          <NoteInputField 
+            maxLength={500} 
+            required={true} 
+            onSubmit={handleCreateNote}
+          />
+        </div>
+        
+        <div>
+          <ItemNotesList 
+            noteItems={notes} 
+            state={notes.length > 0 ? 'success' : 'idle'} 
+          />
+        </div>
+      </div>
+    </div>
+  );
+}
\ No newline at end of file
diff --git a/app/layout.tsx b/app/layout.tsx
index 4fbf3c9..f71000e 100644
--- a/app/layout.tsx
+++ b/app/layout.tsx
@@ -1,5 +1,7 @@
 import type { Metadata } from "next";
 import "./globals.css";
+import Navbar from "@/components/Navbar";
+import Footer from "@/components/Footer";
 
 export const metadata: Metadata = {
   title: "Auto-Forge Generated App",
@@ -13,7 +15,11 @@ export default function RootLayout({
 }>) {
   return (
     <html lang="en">
-      <body>{children}</body>
+      <body>
+        <Navbar />
+        <main>{children}</main>
+        <Footer />
+      </body>
     </html>
   );
 }
diff --git a/app/page.tsx b/app/page.tsx
index 2c8ea46..ea2b205 100644
--- a/app/page.tsx
+++ b/app/page.tsx
@@ -1,3 +1,5 @@
+import Link from "next/link";
+
 export default function HomePage() {
   return (
     <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
@@ -6,6 +8,7 @@ export default function HomePage() {
       <nav>
         <ul>
           {/* FEATURE_LINKS_START */}
+          <li><Link href="/item-notes">Item Notes</Link></li>
           {/* FEATURE_LINKS_END */}
         </ul>
       </nav>
diff --git a/components/Footer.css b/components/Footer.css
new file mode 100644
index 0000000..a0c935f
--- /dev/null
+++ b/components/Footer.css
@@ -0,0 +1,17 @@
+.footer {
+  background-color: #333;
+  color: #fff;
+  text-align: center;
+  padding: 1rem 0;
+  margin-top: auto;
+}
+
+.footer-container {
+  max-width: 1200px;
+  margin: 0 auto;
+  padding: 0 2rem;
+}
+
+.footer-text {
+  margin: 0;
+}
\ No newline at end of file
diff --git a/components/Footer.tsx b/components/Footer.tsx
new file mode 100644
index 0000000..2833aaa
--- /dev/null
+++ b/components/Footer.tsx
@@ -0,0 +1,15 @@
+"use client";
+
+import "./Footer.css";
+
+export default function Footer() {
+  return (
+    <footer className="footer">
+      <div className="footer-container">
+        <p className="footer-text">
+          &copy; {new Date().getFullYear()} Auto-Forge Generated App. All rights reserved.
+        </p>
+      </div>
+    </footer>
+  );
+}
\ No newline at end of file
diff --git a/components/ItemNotesList.jsx b/components/ItemNotesList.jsx
new file mode 100644
index 0000000..04c76eb
--- /dev/null
+++ b/components/ItemNotesList.jsx
@@ -0,0 +1,51 @@
+"use client";
+
+export default function ItemNotesList(props) {
+  const { noteItems } = props;
+
+  if (noteItems === undefined || noteItems.length === 0) {
+    return (
+      <div className="flex justify-center p-4">
+        <p className="text-lg">No notes available.</p>
+      </div>
+    );
+  }
+
+  if (props.state === 'loading') {
+    return (
+      <div className="flex justify-center p-4">
+        <p className="text-lg">Loading...</p>
+      </div>
+    );
+  }
+
+  if (props.state === 'error') {
+    return (
+      <div className="flex justify-center p-4">
+        <p className="text-lg">Error occurred.</p>
+      </div>
+    );
+  }
+
+  if (props.state === 'success') {
+    return (
+      <ul className="list-none flex flex-col gap-2">
+        {noteItems.map((item) => (
+          <li key={item.id} className="bg-white p-4 rounded shadow-md">
+            <p className="text-lg">{item.content}</p>
+          </li>
+        ))}
+      </ul>
+    );
+  }
+
+  return (
+    <ul className="list-none flex flex-col gap-2">
+      {noteItems.map((item) => (
+        <li key={item.id} className="bg-white p-4 rounded shadow-md">
+          <p className="text-lg">{item.content}</p>
+        </li>
+      ))}
+    </ul>
+  );
+}
\ No newline at end of file
diff --git a/components/Navbar.css b/components/Navbar.css
new file mode 100644
index 0000000..39395a6
--- /dev/null
+++ b/components/Navbar.css
@@ -0,0 +1,42 @@
+.navbar {
+  background-color: #333;
+  padding: 1rem 0;
+  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
+}
+
+.navbar-container {
+  max-width: 1200px;
+  margin: 0 auto;
+  display: flex;
+  justify-content: space-between;
+  align-items: center;
+  padding: 0 2rem;
+}
+
+.navbar-logo {
+  color: #fff;
+  font-size: 1.5rem;
+  font-weight: bold;
+  text-decoration: none;
+}
+
+.navbar-menu {
+  display: flex;
+  list-style: none;
+  margin: 0;
+  padding: 0;
+}
+
+.navbar-item {
+  margin: 0 1rem;
+}
+
+.navbar-link {
+  color: #fff;
+  text-decoration: none;
+  transition: color 0.3s ease;
+}
+
+.navbar-link:hover {
+  color: #f0f0f0;
+}
\ No newline at end of file
diff --git a/components/Navbar.tsx b/components/Navbar.tsx
new file mode 100644
index 0000000..95a979a
--- /dev/null
+++ b/components/Navbar.tsx
@@ -0,0 +1,28 @@
+"use client";
+
+import Link from "next/link";
+import "./Navbar.css";
+
+export default function Navbar() {
+  return (
+    <nav className="navbar">
+      <div className="navbar-container">
+        <Link href="/" className="navbar-logo">
+          Auto-Forge App
+        </Link>
+        <ul className="navbar-menu">
+          <li className="navbar-item">
+            <Link href="/" className="navbar-link">
+              Home
+            </Link>
+          </li>
+          <li className="navbar-item">
+            <Link href="/item-notes" className="navbar-link">
+              Item Notes
+            </Link>
+          </li>
+        </ul>
+      </div>
+    </nav>
+  );
+}
\ No newline at end of file
diff --git a/components/NoteInputField.jsx b/components/NoteInputField.jsx
new file mode 100644
index 0000000..057baa6
--- /dev/null
+++ b/components/NoteInputField.jsx
@@ -0,0 +1,73 @@
+"use client";
+
+import React, { useState } from "react";
+
+export default function NoteInputField(props) {
+  const [state, setState] = useState({
+    idle: { text: '', error: '' },
+    loading: { text: '', error: '' },
+    error: { text: '', error: 'Error adding note' },
+    success: { text: '', error: '' }
+  });
+
+  const handleInputChange = (e) => {
+    setState({ idle: { text: e.target.value, error: '' } });
+  };
+
+  const handleSubmit = (e) => {
+    e.preventDefault();
+    if (props.onSubmit && state.idle.text.trim()) {
+      props.onSubmit(state.idle.text.trim());
+    }
+  };
+
+  if (props.state === 'loading') {
+    return (
+      <div className="flex justify-center items-center h-screen">
+        <svg
+          xmlns="http://www.w3.org/2000/svg"
+          fill="none"
+          stroke="currentColor"
+          strokeWidth={2}
+          className="animate-spin h-12 w-12 text-gray-500"
+          viewBox="25 25 50 50">
+          <circle cx={35} cy={35} r={20} fill="none" />
+        </svg>
+      </div>
+    );
+  } else if (props.state === 'error') {
+    return (
+      <div className="flex justify-center items-center h-screen">
+        <p className="text-red-500">{state.error.text}</p>
+      </div>
+    );
+  } else if (props.state === 'success') {
+    return (
+      <div className="flex justify-center items-center h-screen">
+        <p className="text-green-500">Note added successfully!</p>
+      </div>
+    );
+  }
+
+  return (
+    <div className="flex flex-col justify-center items-center h-screen">
+      <form onSubmit={handleSubmit} className="w-full max-w-md">
+        <input
+          type="text"
+          maxLength={props.maxLength}
+          required={props.required}
+          value={state.idle.text}
+          onChange={handleInputChange}
+          placeholder="Add a note..."
+          className="block w-full px-4 py-2 text-gray-700 bg-white border border-gray-200 rounded-md focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-200"
+        />
+        <button
+          type="submit"
+          className="mt-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
+        >
+          Add Note
+        </button>
+      </form>
+    </div>
+  );
+}
\ No newline at end of file
diff --git a/lib/api/itemNotes.ts b/lib/api/itemNotes.ts
new file mode 100644
index 0000000..63c3727
--- /dev/null
+++ b/lib/api/itemNotes.ts
@@ -0,0 +1,21 @@
+export async function listItemNotes(itemId: string) {
+  const response = await fetch(`/api/item-notes?itemId=${itemId}`);
+  if (!response.ok) {
+    throw new Error("Failed to fetch item notes");
+  }
+  return response.json();
+}
+
+export async function createItemNote(itemId: string, content: string) {
+  const response = await fetch("/api/item-notes", {
+    method: "POST",
+    headers: {
+      "Content-Type": "application/json",
+    },
+    body: JSON.stringify({ itemId, content }),
+  });
+  if (!response.ok) {
+    throw new Error("Failed to create item note");
+  }
+  return response.json();
+}
\ No newline at end of file
diff --git a/models/ItemNote.ts b/models/ItemNote.ts
new file mode 100644
index 0000000..65c4c0f
--- /dev/null
+++ b/models/ItemNote.ts
@@ -0,0 +1,10 @@
+import mongoose, { Schema } from "mongoose";
+
+const itemNoteSchema = new Schema({
+  itemId: { type: String, required: true },
+  content: { type: String, required: true, maxlength: 500 },
+  authorId: { type: String, required: true },
+  createdAt: { type: Date, default: Date.now }
+});
+
+export default mongoose.models.ItemNote || mongoose.model("ItemNote", itemNoteSchema);
\ No newline at end of file
diff --git a/next.config.mjs b/next.config.mjs
new file mode 100644
index 0000000..671c0ed
--- /dev/null
+++ b/next.config.mjs
@@ -0,0 +1,4 @@
+/** @type {import('next').NextConfig} */
+const nextConfig = {};
+
+export default nextConfig;
diff --git a/next.config.ts b/next.config.ts
deleted file mode 100644
index 6d94fc0..0000000
--- a/next.config.ts
+++ /dev/null
@@ -1,5 +0,0 @@
-import type { NextConfig } from "next";
-
-const nextConfig: NextConfig = {};
-
-export default nextConfig;
diff --git a/package-lock.json b/package-lock.json
new file mode 100644
index 0000000..c4fbfcf
--- /dev/null
+++ b/package-lock.json
@@ -0,0 +1,5625 @@
+{
+  "name": "auto-forge-generated-app",
+  "lockfileVersion": 3,
+  "requires": true,
+  "packages": {
+    "": {
+      "name": "auto-forge-generated-app",
+      "dependencies": {
+        "mongoose": "8.5.0",
+        "next": "14.2.5",
+        "react": "18.3.1",
+        "react-dom": "18.3.1"
+      },
+      "devDependencies": {
+        "@types/node": "20.14.15",
+        "@types/react": "18.3.3",
+        "@types/react-dom": "18.3.0",
+        "eslint": "8.57.0",
+        "eslint-config-next": "14.2.5",
+        "typescript": "5.5.4"
+      }
+    },
+    "node_modules/@emnapi/core": {
+      "version": "1.10.0",
+      "resolved": "https://registry.npmjs.org/@emnapi/core/-/core-1.10.0.tgz",
+      "integrity": "sha512-yq6OkJ4p82CAfPl0u9mQebQHKPJkY7WrIuk205cTYnYe+k2Z8YBh11FrbRG/H6ihirqcacOgl2BIO8oyMQLeXw==",
+      "dev": true,
+      "license": "MIT",
+      "optional": true,
+      "dependencies": {
+        "@emnapi/wasi-threads": "1.2.1",
+        "tslib": "^2.4.0"
+      }
+    },
+    "node_modules/@emnapi/runtime": {
+      "version": "1.10.0",
+      "resolved": "https://registry.npmjs.org/@emnapi/runtime/-/runtime-1.10.0.tgz",
+      "integrity": "sha512-ewvYlk86xUoGI0zQRNq/mC+16R1QeDlKQy21Ki3oSYXNgLb45GV1P6A0M+/s6nyCuNDqe5VpaY84BzXGwVbwFA==",
+      "dev": true,
+      "license": "MIT",
+      "optional": true,
+      "dependencies": {
+        "tslib": "^2.4.0"
+      }
+    },
+    "node_modules/@emnapi/wasi-threads": {
+      "version": "1.2.1",
+      "resolved": "https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.1.tgz",
+      "integrity": "sha512-uTII7OYF+/Mes/MrcIOYp5yOtSMLBWSIoLPpcgwipoiKbli6k322tcoFsxoIIxPDqW01SQGAgko4EzZi2BNv2w==",
+      "dev": true,
+      "license": "MIT",
+      "optional": true,
+      "dependencies": {
+        "tslib": "^2.4.0"
+      }
+    },
+    "node_modules/@eslint-community/eslint-utils": {
+      "version": "4.10.1",
+      "resolved": "https://registry.npmjs.org/@eslint-community/eslint-utils/-/eslint-utils-4.10.1.tgz",
+      "integrity": "sha512-cuadcxVFE8sDK6iWJbs8Sn0av2Nrh2QSGQhVlBW9AaAHqHwjWsZHT8LJ4hFGPh7ASBV2deFdM7H/DPjulmh8rg==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "eslint-visitor-keys": "^3.4.3"
+      },
+      "engines": {
+        "node": "^12.22.0 || ^14.17.0 || >=16.0.0"
+      },
+      "funding": {
+        "url": "https://opencollective.com/eslint"
+      },
+      "peerDependencies": {
+        "eslint": "^6.0.0 || ^7.0.0 || >=8.0.0"
+      }
+    },
+    "node_modules/@eslint-community/regexpp": {
+      "version": "4.12.2",
+      "resolved": "https://registry.npmjs.org/@eslint-community/regexpp/-/regexpp-4.12.2.tgz",
+      "integrity": "sha512-EriSTlt5OC9/7SXkRSCAhfSxxoSUgBm33OH+IkwbdpgoqsSsUg7y3uh+IICI/Qg4BBWr3U2i39RpmycbxMq4ew==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": "^12.0.0 || ^14.0.0 || >=16.0.0"
+      }
+    },
+    "node_modules/@eslint/eslintrc": {
+      "version": "2.1.4",
+      "resolved": "https://registry.npmjs.org/@eslint/eslintrc/-/eslintrc-2.1.4.tgz",
+      "integrity": "sha512-269Z39MS6wVJtsoUl10L60WdkhJVdPG24Q4eZTH3nnF6lpvSShEK3wQjDX9JRWAUPvPh7COouPpU9IrqaZFvtQ==",
+      "dev": true,
+      "license": "MIT",
+      "dependencies": {
+        "ajv": "^6.12.4",
+        "debug": "^4.3.2",
+        "espree": "^9.6.0",
+        "globals": "^13.19.0",
+        "ignore": "^5.2.0",
+        "import-fresh": "^3.2.1",
+        "js-yaml": "^4.1.0",
+        "minimatch": "^3.1.2",
+        "strip-json-comments": "^3.1.1"
+      },
+      "engines": {
+        "node": "^12.22.0 || ^14.17.0 || >=16.0.0"
+      },
+      "funding": {
+        "url": "https://opencollective.com/eslint"
+      }
+    },
+    "node_modules/@eslint/js": {
+      "version": "8.57.0",
+      "resolved": "https://registry.npmjs.org/@eslint/js/-/js-8.57.0.tgz",
+      "integrity": "sha512-Ys+3g2TaW7gADOJzPt83SJtCDhMjndcDMFVQ/Tj9iA1BfJzFKD9mAUXT3OenpuPHbI6P/myECxRJrofUsDx/5g==",
+      "dev": true,
+      "license": "MIT",
+      "engines": {
+        "node": "^12.22.0 || ^14.17.0 || >=16.0.0"
+      }
+    },
+    "node_modules/@humanwhocodes/config-array": {
+      "version": "0.11.14",
+      "resolved": "https://registry.npmjs.org/@humanwhocodes/config-array/-/config-array-0.11.14.tgz",
+      "integrity": "sha512-3T8LkOmg45BV5FICb15QQMsyUSWrQ8AygVfC7ZG32zOalnqrilm018ZVCw0eapXux8FtA33q8PSRSstjee3jSg==",
+      "deprecated": "Use @eslint/config-array instead",
+      "dev": true,
+      "license": "Apache-2.0",
+      "dependencies": {
+        "@humanwhocodes/object-schema": "^2.0.2",
+        "debug": "^4.3.1",
+        "minimatch": "^3.0.5"
+      },
+      "engines": {
+        "node": ">=10.10.0"
+      }
+    },
+    "node_modules/@humanwhocodes/module-importer": {
+      "version": "1.0.1",
+      "resolved": "https://registry.npmjs.org/@humanwhocodes/module-importer/-/module-importer-1.0.1.tgz",
+      "integrity": "sha512-bxveV4V8v5Yb4ncFTT3rPSgZBOpCkjfK0y4oVVVJwIuDVBRMDXrPyXRL988i5ap9m9bnyEEjWfm5WkBmtffLfA==",
+      "dev": true,
+      "license": "Apache-2.0",
+      "engines": {
+        "node": ">=12.22"
+      },
+      "funding": {
+        "type": "github",
+        "url": "https://github.com/sponsors/nzakas"
+      }
+    },
+    "node_modules/@humanwhocodes/object-schema": {
+      "version": "2.0.3",
+      "resolved": "https://registry.npmjs.org/@humanwhocodes/object-schema/-/object-schema-2.0.3.tgz",
+      "integrity": "sha512-93zYdMES/c1D69yZiKDBj0V24vqNzB/koF26KPaagAfd3P/4gUlh3Dys5ogAK+Exi9QyzlD8x/08Zt7wIKcDcA==",
+      "deprecated": "Use @eslint/object-schema instead",
+      "dev": true,
+      "license": "BSD-3-Clause"
+    },
+    "node_modules/@isaacs/cliui": {
+      "version": "8.0.2",
+      "resolved": "https://registry.npmjs.org/@isaacs/cliui/-/cliui-8.0.2.tgz",
+      "integrity": "sha512-O8jcjabXaleOG9DQ0+ARXWZBTfnP4WNAqzui
```