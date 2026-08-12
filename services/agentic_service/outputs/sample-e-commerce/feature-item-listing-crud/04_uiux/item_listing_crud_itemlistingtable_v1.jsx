export default function ItemListingTable(props) {
  const { items } = props;

  if (items.length === 0) {
    return (
      <div className="flex justify-center p-10">
        <p className="text-lg">No items found.</p>
      </div>
    );
  }

  if (props.state === 'loading') {
    return (
      <div className="flex justify-center p-10">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  if (props.state === 'error') {
    return (
      <div className="flex justify-center p-10">
        <p className="text-lg">Error occurred.</p>
      </div>
    );
  }

  if (props.state === 'success') {
    return (
      <table className="w-full border-collapse border">
        <thead>
          <tr>
            <th className="px-4 py-2">Name</th>
            <th className="px-4 py-2">Description</th>
            <th className="px-4 py-2">Price</th>
            <th className="px-4 py-2">Quantity</th>
            <th className="px-4 py-2">Category</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className="hover:bg-gray-100">
              <td className="px-4 py-2">{item.name}</td>
              <td className="px-4 py-2">{item.description}</td>
              <td className="px-4 py-2">${item.price.toFixed(2)}</td>
              <td className="px-4 py-2">{item.quantity}</td>
              <td className="px-4 py-2">{item.category}</td>
            </tr>
          ))}
        </tbody>
      </table>
    );
  }

  return (
    <div className="flex justify-center p-10">
      <p className="text-lg">Unknown state.</p>
    </div>
  );
}