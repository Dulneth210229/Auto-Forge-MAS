export default function UpdateItemForm(props) {
  const [state, setState] = React.useState("idle");

  if (state === "loading") {
    return (
      <div className="flex justify-center items-center h-screen">
        <form>
          {props.itemName && (
            <label
              htmlFor="itemName"
              className="block text-sm font-bold mb-2"
            >
              Item Name:
            </label>
          )}
          {props.itemName && (
            <input
              type="text"
              id="itemName"
              value={props.itemName}
              onChange={() => setState("idle")}
              className="w-full p-2 text-gray-700 focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
            />
          )}
          {props.itemDescription && (
            <label
              htmlFor="itemDescription"
              className="block text-sm font-bold mb-2"
            >
              Item Description:
            </label>
          )}
          {props.itemDescription && (
            <textarea
              id="itemDescription"
              value={props.itemDescription}
              onChange={() => setState("idle")}
              className="w-full p-2 text-gray-700 focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md h-40"
            />
          )}
          {props.itemPrice && (
            <label
              htmlFor="itemPrice"
              className="block text-sm font-bold mb-2"
            >
              Item Price:
            </label>
          )}
          {props.itemPrice && (
            <input
              type="text"
              id="itemPrice"
              value={props.itemPrice}
              onChange={() => setState("idle")}
              className="w-full p-2 text-gray-700 focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
            />
          )}
          {props.itemStockQuantity && (
            <label
              htmlFor="itemStockQuantity"
              className="block text-sm font-bold mb-2"
            >
              Item Stock Quantity:
            </label>
          )}
          {props.itemStockQuantity && (
            <input
              type="text"
              id="itemStockQuantity"
              value={props.itemStockQuantity}
              onChange={() => setState("idle")}
              className="w-full p-2 text-gray-700 focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
            />
          )}
          {props.itemSKU && (
            <label
              htmlFor="itemSKU"
              className="block text-sm font-bold mb-2"
            >
              Item SKU:
            </label>
          )}
          {props.itemSKU && (
            <input
              type="text"
              id="itemSKU"
              value={props.itemSKU}
              onChange={() => setState("idle")}
              className="w-full p-2 text-gray-700 focus:ring-indigo-500 focus:border-indigo-500 block sm:text-sm border-gray-300 rounded-md"
            />
          )}
          {state !== "loading" && (
            <button
              type="submit"
              onClick={() => setState("loading")}
              className="bg-orange-500 hover:bg-orange-700 text-white font-bold py-2 px-4 rounded"
            >
              Update Item
            </button>
          )}
        </form>
      </div>
    );
  } else if (state === "error") {
    return (
      <div className="bg-red-100 border-l-4 border-red-500 p-4">
        <h5 className="font-bold">Error</h5>
        <p>Something went wrong.</p>
      </div>
    );
  } else if (state === "success") {
    return (
      <div className="bg-green-100 border-l-4 border-green-500 p-4">
        <h5 className="font-bold">Success</h5>
        <p>Item updated successfully.</p>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center h-screen">
      <form onSubmit={() => setState("loading")}>
        {/* form fields */}
      </form>
    </div>
  );
}