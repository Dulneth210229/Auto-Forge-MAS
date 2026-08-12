export default function ItemList(props) {
  const { state, items } = props;

  return (
    <div className="flex flex-col gap-4">
      {(state === 'idle' || state === 'success') && (
        <ul className="list-disc list-inside">
          {items.map((item, index) => (
            <li key={index} className="bg-white p-2 rounded shadow-md">
              <span className="font-bold">{item.itemName}</span>
              <p>{item.itemDescription}</p>
              <p>Price: {item.itemPrice}</p>
              <p>Stock Quantity: {item.itemStockQuantity}</p>
              <p>Sku: {item.itemSKU}</p>
            </li>
          ))}
        </ul>
      )}
      {(state === 'loading') && (
        <div className="flex justify-center">
          <svg
            className="animate-spin h-5 w-5 text-gray-500"
            viewBox="0 0 24 24"
          >
            <circle className="opacity-25" cx={12} cy={12} r={12} />
          </svg>
        </div>
      )}
      {(state === 'error') && (
        <p className="text-red-500">Error occurred</p>
      )}
    </div>
  );
}