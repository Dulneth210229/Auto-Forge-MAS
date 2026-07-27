export default function CommentList(props) {
  const { comments, currentUser, state } = props;
  
  if (state === 'loading') {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-lg shadow p-4 animate-pulse">
            <div className="flex items-center space-x-3 mb-2">
              <div className="w-8 h-8 bg-gray-200 rounded-full"></div>
              <div className="h-4 bg-gray-200 rounded w-1/4"></div>
            </div>
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }
  
  if (state === 'error') {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        Failed to load comments. Please try again later.
      </div>
    );
  }
  
  if (state === 'idle') {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
        No comments yet. Be the first to comment!
      </div>
    );
  }
  
  if (state === 'success' && (!comments || comments.length === 0)) {
    return (
      <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center text-gray-500">
        No comments yet. Be the first to comment!
      </div>
    );
  }
  
  return (
    <div className="space-y-4">
      {comments.map((comment) => {
        const isCurrentUser = comment.authorUserId === currentUser.id;
        const timestamp = new Date(comment.createdTimestamp).toLocaleString();
        
        return (
          <div key={comment.id} className="bg-white rounded-lg shadow p-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center text-white font-medium">
                  {comment.authorUserId.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="font-medium text-gray-900">User {comment.authorUserId}</div>
                  <div className="text-xs text-gray-500">{timestamp}</div>
                </div>
              </div>
              {isCurrentUser && (
                <button 
                  className="text-gray-400 hover:text-red-500 transition-colors"
                  aria-label="Delete comment"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </button>
              )}
            </div>
            <p className="mt-3 text-gray-700">{comment.commentText}</p>
          </div>
        );
      })}
    </div>
  );
}