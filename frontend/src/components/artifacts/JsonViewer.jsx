import { JsonView, allExpanded, defaultStyles } from "react-json-view-lite";
import "react-json-view-lite/dist/index.css";

export default function JsonViewer({ data }) {
  if (data == null) {
    return <p className="text-gray-500 text-sm">This artifact's JSON could not be parsed.</p>;
  }

  return (
    <div className="text-sm">
      <JsonView data={data} shouldExpandNode={allExpanded} style={defaultStyles} />
    </div>
  );
}
