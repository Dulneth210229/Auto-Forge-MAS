# Merge Report: Task Comments

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
  - client/src/pages/TaskDetailPage.jsx:11: const [currentUser] = useState({ id: "user123", username: "testuser" }); // Mock user for now
  ```

## Files changed
### Added
- `client/src/components/CommentInput.jsx`
- `client/src/components/CommentItem.jsx`
- `client/src/components/CommentList.jsx`
- `client/src/pages/TaskDetailPage.jsx`
- `client/src/services/taskCommentsService.js`
- `server/src/models/Comment.js`
- `server/src/routes/task-comments.routes.js`
### Modified
- `client/src/App.jsx`
- `server/src/app.js`

## Full diff
```diff
diff --git a/client/src/App.jsx b/client/src/App.jsx
index 3259afd..d76e458 100644
--- a/client/src/App.jsx
+++ b/client/src/App.jsx
@@ -1,5 +1,6 @@
 import React from "react";
 import { Routes, Route } from "react-router-dom";
+import TaskDetailPage from "./pages/TaskDetailPage";
 
 function HomePage() {
   return (
@@ -14,6 +15,7 @@ export default function App() {
   return (
     <Routes>
       <Route path="/" element={<HomePage />} />
+      <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
     </Routes>
   );
 }
diff --git a/client/src/components/CommentInput.jsx b/client/src/components/CommentInput.jsx
new file mode 100644
index 0000000..99571b0
--- /dev/null
+++ b/client/src/components/CommentInput.jsx
@@ -0,0 +1,47 @@
+import React, { useState } from "react";
+
+function CommentInput({ onSubmit, taskId }) {
+  const [text, setText] = useState("");
+
+  const handleSubmit = (e) => {
+    e.preventDefault();
+    if (text.trim()) {
+      onSubmit(taskId, text.trim());
+      setText("");
+    }
+  };
+
+  return (
+    <form onSubmit={handleSubmit} style={{ marginBottom: "1rem" }}>
+      <div style={{ display: "flex", gap: "0.5rem" }}>
+        <input
+          type="text"
+          value={text}
+          onChange={(e) => setText(e.target.value)}
+          placeholder="Add a comment..."
+          style={{
+            flex: 1,
+            padding: "0.5rem",
+            border: "1px solid #ccc",
+            borderRadius: "4px"
+          }}
+        />
+        <button
+          type="submit"
+          style={{
+            padding: "0.5rem 1rem",
+            backgroundColor: "#007bff",
+            color: "white",
+            border: "none",
+            borderRadius: "4px",
+            cursor: "pointer"
+          }}
+        >
+          Add Comment
+        </button>
+      </div>
+    </form>
+  );
+}
+
+export default CommentInput;
\ No newline at end of file
diff --git a/client/src/components/CommentItem.jsx b/client/src/components/CommentItem.jsx
new file mode 100644
index 0000000..e853cd0
--- /dev/null
+++ b/client/src/components/CommentItem.jsx
@@ -0,0 +1,50 @@
+import React from "react";
+
+function CommentItem({ comment, currentUser, onDelete }) {
+  const isAuthor = comment.author._id === currentUser.id;
+
+  const handleDelete = () => {
+    if (isAuthor) {
+      onDelete(comment._id);
+    }
+  };
+
+  return (
+    <div 
+      style={{ 
+        border: "1px solid #eee", 
+        borderRadius: "4px", 
+        padding: "1rem", 
+        marginBottom: "0.5rem",
+        backgroundColor: "#f9f9f9"
+      }}
+    >
+      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
+        <div>
+          <strong>{comment.author.username}</strong>
+          <p>{comment.text}</p>
+          <small style={{ color: "#666" }}>
+            {new Date(comment.createdAt).toLocaleString()}
+          </small>
+        </div>
+        {isAuthor && (
+          <button
+            onClick={handleDelete}
+            style={{
+              backgroundColor: "#dc3545",
+              color: "white",
+              border: "none",
+              borderRadius: "4px",
+              padding: "0.25rem 0.5rem",
+              cursor: "pointer"
+            }}
+          >
+            Delete
+          </button>
+        )}
+      </div>
+    </div>
+  );
+}
+
+export default CommentItem;
\ No newline at end of file
diff --git a/client/src/components/CommentList.jsx b/client/src/components/CommentList.jsx
new file mode 100644
index 0000000..8187b92
--- /dev/null
+++ b/client/src/components/CommentList.jsx
@@ -0,0 +1,23 @@
+import React from "react";
+import CommentItem from "./CommentItem";
+
+function CommentList({ comments, currentUser, onDelete }) {
+  if (comments.length === 0) {
+    return <p>No comments yet.</p>;
+  }
+
+  return (
+    <div>
+      {comments.map((comment) => (
+        <CommentItem
+          key={comment._id}
+          comment={comment}
+          currentUser={currentUser}
+          onDelete={onDelete}
+        />
+      ))}
+    </div>
+  );
+}
+
+export default CommentList;
\ No newline at end of file
diff --git a/client/src/pages/TaskDetailPage.jsx b/client/src/pages/TaskDetailPage.jsx
new file mode 100644
index 0000000..21cf85f
--- /dev/null
+++ b/client/src/pages/TaskDetailPage.jsx
@@ -0,0 +1,76 @@
+import React, { useState, useEffect } from "react";
+import { useParams } from "react-router-dom";
+import { taskCommentsService } from "../services/taskCommentsService";
+import CommentList from "../components/CommentList";
+import CommentInput from "../components/CommentInput";
+
+function TaskDetailPage() {
+  const { taskId } = useParams();
+  const [comments, setComments] = useState([]);
+  const [loading, setLoading] = useState(true);
+  const [currentUser] = useState({ id: "user123", username: "testuser" }); // Mock user for now
+
+  useEffect(() => {
+    const fetchComments = async () => {
+      try {
+        const fetchedComments = await taskCommentsService.getComments(taskId);
+        setComments(fetchedComments);
+        setLoading(false);
+      } catch (error) {
+        console.error("Error fetching comments:", error);
+        setLoading(false);
+      }
+    };
+
+    fetchComments();
+  }, [taskId]);
+
+  const handleAddComment = async (taskId, text) => {
+    try {
+      const newComment = await taskCommentsService.createComment({
+        text,
+        author: currentUser.id,
+        task: taskId
+      });
+      
+      // Add the new comment to the beginning of the list
+      setComments(prevComments => [newComment, ...prevComments]);
+    } catch (error) {
+      console.error("Error adding comment:", error);
+    }
+  };
+
+  const handleDeleteComment = async (commentId) => {
+    try {
+      await taskCommentsService.deleteComment(commentId, currentUser.id);
+      
+      // Remove the deleted comment from the list
+      setComments(prevComments => 
+        prevComments.filter(comment => comment._id !== commentId)
+      );
+    } catch (error) {
+      console.error("Error deleting comment:", error);
+    }
+  };
+
+  if (loading) {
+    return <div>Loading task details...</div>;
+  }
+
+  return (
+    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
+      <h1>Task Details</h1>
+      <p>Task ID: {taskId}</p>
+      
+      <h2>Comments</h2>
+      <CommentInput onSubmit={handleAddComment} taskId={taskId} />
+      <CommentList 
+        comments={comments} 
+        currentUser={currentUser}
+        onDelete={handleDeleteComment}
+      />
+    </div>
+  );
+}
+
+export default TaskDetailPage;
\ No newline at end of file
diff --git a/client/src/services/taskCommentsService.js b/client/src/services/taskCommentsService.js
new file mode 100644
index 0000000..9909b3c
--- /dev/null
+++ b/client/src/services/taskCommentsService.js
@@ -0,0 +1,63 @@
+const API_BASE_URL = "/api";
+
+export const taskCommentsService = {
+  // Get all comments for a specific task
+  async getComments(taskId) {
+    try {
+      const response = await fetch(`${API_BASE_URL}/task-comments/${taskId}`);
+      if (!response.ok) {
+        throw new Error(`Failed to fetch comments: ${response.status}`);
+      }
+      const comments = await response.json();
+      return comments;
+    } catch (error) {
+      console.error("Error fetching comments:", error);
+      throw error;
+    }
+  },
+
+  // Create a new comment
+  async createComment(commentData) {
+    try {
+      const response = await fetch(`${API_BASE_URL}/task-comments`, {
+        method: "POST",
+        headers: {
+          "Content-Type": "application/json",
+        },
+        body: JSON.stringify(commentData),
+      });
+      
+      if (!response.ok) {
+        throw new Error(`Failed to create comment: ${response.status}`);
+      }
+      
+      const newComment = await response.json();
+      return newComment;
+    } catch (error) {
+      console.error("Error creating comment:", error);
+      throw error;
+    }
+  },
+
+  // Delete a comment
+  async deleteComment(commentId, authorId) {
+    try {
+      const response = await fetch(`${API_BASE_URL}/task-comments/${commentId}`, {
+        method: "DELETE",
+        headers: {
+          "Content-Type": "application/json",
+        },
+        body: JSON.stringify({ authorId }),
+      });
+      
+      if (!response.ok) {
+        throw new Error(`Failed to delete comment: ${response.status}`);
+      }
+      
+      return await response.json();
+    } catch (error) {
+      console.error("Error deleting comment:", error);
+      throw error;
+    }
+  }
+};
\ No newline at end of file
diff --git a/server/src/app.js b/server/src/app.js
index 5c48c31..9a7e617 100644
--- a/server/src/app.js
+++ b/server/src/app.js
@@ -22,6 +22,8 @@ app.get("/api/health", (req, res) => {
 });
 
 // FEATURE_ROUTES_START
+const taskCommentsRoutes = require("./routes/task-comments.routes");
+app.use("/api/", taskCommentsRoutes);
 // FEATURE_ROUTES_END
 
 app.use((err, req, res, next) => {
diff --git a/server/src/models/Comment.js b/server/src/models/Comment.js
new file mode 100644
index 0000000..ee56546
--- /dev/null
+++ b/server/src/models/Comment.js
@@ -0,0 +1,25 @@
+const mongoose = require("mongoose");
+
+const commentSchema = new mongoose.Schema({
+  text: {
+    type: String,
+    required: true,
+    trim: true
+  },
+  author: {
+    type: mongoose.Schema.Types.ObjectId,
+    ref: "User",
+    required: true
+  },
+  task: {
+    type: mongoose.Schema.Types.ObjectId,
+    ref: "Task",
+    required: true
+  },
+  createdAt: {
+    type: Date,
+    default: Date.now
+  }
+});
+
+module.exports = mongoose.model("Comment", commentSchema);
\ No newline at end of file
diff --git a/server/src/routes/task-comments.routes.js b/server/src/routes/task-comments.routes.js
new file mode 100644
index 0000000..d0ed7b8
--- /dev/null
+++ b/server/src/routes/task-comments.routes.js
@@ -0,0 +1,77 @@
+const express = require("express");
+const router = express.Router();
+const Comment = require("../models/Comment");
+
+// Get all comments for a specific task, ordered by creation date
+router.get("/api/task-comments/:taskId", async (req, res) => {
+  try {
+    const comments = await Comment.find({ task: req.params.taskId })
+      .populate("author", "username")
+      .sort({ createdAt: -1 });
+    
+    res.json(comments);
+  } catch (error) {
+    res.status(500).json({ error: error.message });
+  }
+});
+
+// Create a new comment
+router.post("/api/task-comments", async (req, res) => {
+  try {
+    const { text, author, task } = req.body;
+    
+    // Validate required fields
+    if (!text || !author || !task) {
+      return res.status(400).json({ 
+        error: "Text, author, and task are required fields" 
+      });
+    }
+    
+    const comment = new Comment({
+      text,
+      author,
+      task
+    });
+    
+    const savedComment = await comment.save();
+    const populatedComment = await savedComment.populate("author", "username");
+    
+    res.status(201).json(populatedComment);
+  } catch (error) {
+    res.status(500).json({ error: error.message });
+  }
+});
+
+// Delete a comment (only if the requester is the author)
+router.delete("/api/task-comments/:commentId", async (req, res) => {
+  try {
+    const { commentId } = req.params;
+    const { authorId } = req.body; // Author ID should be passed in request body for validation
+    
+    if (!authorId) {
+      return res.status(400).json({ 
+        error: "Author ID is required for comment deletion" 
+      });
+    }
+    
+    const comment = await Comment.findById(commentId);
+    
+    if (!comment) {
+      return res.status(404).json({ error: "Comment not found" });
+    }
+    
+    // Check if the requester is the author of the comment
+    if (comment.author.toString() !== authorId) {
+      return res.status(403).json({ 
+        error: "You do not have permission to delete this comment" 
+      });
+    }
+    
+    await Comment.findByIdAndDelete(commentId);
+    res.json({ message: "Comment deleted successfully" });
+  } catch (error) {
+    res.status(500).json({ error: error.message });
+  }
+});
+
+module.exports = router;
\ No newline at end of file
```