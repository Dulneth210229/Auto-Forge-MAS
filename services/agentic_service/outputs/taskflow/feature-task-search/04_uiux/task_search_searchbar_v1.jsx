export default function SearchBar(props) {
  const { placeholder, state } = props;

  if (state === 'loading') {
    return (
      <div className="flex justify-center items-center">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-6 h-6 text-gray-400 animate-spin">
          <circle cx="12" cy="12" r="10"></circle>
        </svg>
      </div>
    );
  } else if (state === 'error') {
    return (
      <div className="flex justify-center items-center text-red-500">
        Error occurred
      </div>
    );
  } else if (state === 'success') {
    return (
      <div className="flex justify-center items-center text-green-500">
        Search successful!
      </div>
    );
  }

  return (
    <input
      type="search"
      placeholder={placeholder}
      className="w-full p-2 pl-10 text-gray-700 border border-gray-200 rounded-md focus:outline-none focus:border-blue-400"
    />
  );
}