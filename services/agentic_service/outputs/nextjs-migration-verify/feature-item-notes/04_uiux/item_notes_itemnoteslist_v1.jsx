export default function ItemNotesList(props) {
  const { noteItems } = props;

  if (noteItems === undefined || noteItems.length === 0) {
    return (
      <div className="flex justify-center p-4">
        <p className="text-lg">No notes available.</p>
      </div>
    );
  }

  if (props.state === 'loading') {
    return (
      <div className="flex justify-center p-4">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  if (props.state === 'error') {
    return (
      <div className="flex justify-center p-4">
        <p className="text-lg">Error occurred.</p>
      </div>
    );
  }

  if (props.state === 'success') {
    return (
      <ul className="list-none flex flex-col gap-2">
        {noteItems.map((item) => (
          <li key={item.id} className="bg-white p-4 rounded shadow-md">
            <p className="text-lg">{item.content}</p>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <ul className="list-none flex flex-col gap-2">
      {noteItems.map((item) => (
        <li key={item.id} className="bg-white p-4 rounded shadow-md">
          <p className="text-lg">{item.content}</p>
        </li>
      ))}
    </ul>
  );
}