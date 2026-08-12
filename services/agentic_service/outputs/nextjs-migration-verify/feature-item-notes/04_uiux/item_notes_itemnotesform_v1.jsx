export default function ItemNotesForm(props) {
  const { placeholderText, state } = props;

  switch (state) {
    case 'loading':
      return (
        <div className="flex justify-center items-center h-screen">
          <svg
            className="animate-spin h-16 w-16 border-2 border-white rounded-full"
            viewBox="25 25 50 50"
          >
            <circle
              className="opacity-75"
              cx={48}
              cy={48}
              r={24}
              fill="none"
              stroke-width={4}
              stroke="#f0f0f0"
            />
          </svg>
        </div>
      );
    case 'error':
      return (
        <div className="flex justify-center items-center h-screen">
          <p className="text-lg text-red-500">Error occurred!</p>
        </div>
      );
    case 'success':
      return (
        <div className="flex justify-center items-center h-screen">
          <p className="text-lg text-green-500">Note saved successfully!</p>
        </div>
      );
    default: // idle
      return (
        <form className="max-w-md mx-auto p-4 bg-white shadow-md rounded">
          <textarea
            className="w-full h-40 p-2 border border-gray-300 focus:outline-none"
            placeholder={placeholderText}
          />
        </form>
      );
  }
}