// Same color-coding convention SeverityBadge.jsx/StatusBadge.jsx already established -- green
// for a real pass, red for a real fail, gray for skipped (not "bad", just not run/not matched).
const STYLES = {
  passed: "bg-green-100 text-green-800 dark:bg-green-500/15 dark:text-green-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-500/15 dark:text-red-300",
  skipped: "bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-gray-300",
};

const LABELS = { passed: "Passed", failed: "Failed", skipped: "Skipped" };

export default function QaStatusBadge({ status }) {
  const style = STYLES[status] || STYLES.skipped;
  const label = LABELS[status] || status;
  return (
    <span className={`inline-block px-2 py-1 text-xs font-semibold rounded-full ${style}`}>{label}</span>
  );
}
