export default function NoteInputField(props) {
  const [state, setState] = React.useState({
    idle: { text: '', error: '' },
    loading: { text: '', error: '' },
    error: { text: '', error: 'Error adding note' },
    success: { text: '', error: '' }
  });

  if (props.state === 'loading') {
    return (
      <div className="flex justify-center items-center h-screen">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          className="animate-spin h-12 w-12 text-gray-500"
          viewBox="25 25 50 50">
          <circle cx={35} cy={35} r={20} fill="none" />
        </svg>
      </div>
    );
  } else if (props.state === 'error') {
    return (
      <div className="flex justify-center items-center h-screen">
        <p className="text-red-500">{state.error.text}</p>
      </div>
    );
  } else if (props.state === 'success') {
    return (
      <div className="flex justify-center items-center h-screen">
        <p className="text-green-500">Note added successfully!</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col justify-center items-center h-screen">
      {state.idle.text}
      <input
        type="text"
        maxLength={props.maxLength}
        required={props.required}
        value={state.idle.text}
        onChange={(e) => setState({ idle: { text: e.target.value, error: '' } })}
        placeholder="Add a note..."
        className="block w-full px-4 py-2 text-gray-700 bg-white border border-gray-200 rounded-md focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-200"
      />
    </div>
  );
}