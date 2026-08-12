export default function PaginationControls(props) {
  const { state } = props;

  if (state === 'loading') {
    return (
      <div className="flex justify-center items-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
          className="w-6 h-6 text-gray-400 animate-spin"
        >
          <circle cx="12" cy="12" r="12"></circle>
        </svg>
      </div>
    );
  } else if (state === 'error') {
    return (
      <div className="flex justify-center items-center">
        <span className="text-red-500">Error occurred</span>
      </div>
    );
  } else if (state === 'success') {
    return (
      <div className="flex justify-center items-center">
        <span className="text-green-500">Data loaded successfully</span>
      </div>
    );
  }

  return (
    <nav
      aria-label="Pagination"
      className="flex justify-between items-center py-4"
    >
      <button
        className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-2 px-4 rounded"
        disabled={state === 'loading'}
      >
        Previous
      </button>
      <span className="text-gray-500">{/* page number */}</span>
      <button
        className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-2 px-4 rounded"
        disabled={state === 'loading'}
      >
        Next
      </button>
    </nav>
  );
}