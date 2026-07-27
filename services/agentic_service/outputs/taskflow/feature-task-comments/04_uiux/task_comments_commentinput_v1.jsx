export default function CommentInput(props) {
  const [commentText, setCommentText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!commentText.trim()) {
      setSubmitError('Comment cannot be empty');
      return;
    }

    setIsSubmitting(true);
    setSubmitError(null);
    
    try {
      // Mock submission - in real app this would be an API call
      await new Promise(resolve => setTimeout(resolve, 1000));
      // Simulate successful submission
      setCommentText('');
    } catch (error) {
      setSubmitError('Failed to submit comment. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mt-6">
      <form onSubmit={handleSubmit} className="space-y-3">
        <div className="flex items-start space-x-3">
          <div className="flex-1">
            <textarea
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder={props.placeholder}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              rows="3"
              disabled={isSubmitting}
            />
            {submitError && (
              <p className="mt-1 text-sm text-red-600">{submitError}</p>
            )}
          </div>
          <button
            type="submit"
            disabled={isSubmitting || !commentText.trim()}
            className={`self-end px-4 py-2 rounded-lg font-medium transition-colors ${
              isSubmitting || !commentText.trim()
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 text-white hover:bg-blue-700'
            }`}
          >
            {isSubmitting ? 'Posting...' : 'Post'}
          </button>
        </div>
      </form>
    </div>
  );
}