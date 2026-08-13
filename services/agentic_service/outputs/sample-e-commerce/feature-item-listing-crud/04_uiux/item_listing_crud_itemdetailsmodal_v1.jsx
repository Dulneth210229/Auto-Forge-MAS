export default function ItemDetailsModal(props) {
  const { items, state } = props;

  if (state === 'loading') {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 bg-gray-300"></div>
      </div>
    );
  }

  if (state === 'error') {
    return (
      <div className="flex justify-center items-center h-screen">
        <p className="text-lg text-red-500">Error occurred</p>
      </div>
    );
  }

  if (state === 'success') {
    return (
      <div className="flex flex-col gap-4 p-4 max-w-md mx-auto">
        {items.map((item) => (
          <div key={item.id} className="bg-white shadow-md rounded overflow-hidden">
            <img src={item.imageUrl} alt={item.name} className="h-48 w-full object-cover" />
            <h2 className="text-lg font-bold">{item.name}</h2>
            <p className="text-gray-600">{item.description}</p>
            <div className="flex justify-between items-center">
              <span className="text-lg text-green-500">Price: ${item.price}</span>
              <span className="text-lg text-gray-600">Quantity: {item.quantity}</span>
              <button className="bg-orange-500 hover:bg-orange-700 text-white font-bold py-2 px-4 rounded">
                Edit
              </button>
              <button className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded">
                Delete
              </button>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center h-screen">
      <p className="text-lg text-gray-500">No data available</p>
    </div>
  );
}