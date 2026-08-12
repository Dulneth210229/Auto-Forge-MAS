export default function TaskList(props) {
  const { tasks } = props;

  if (tasks.length === 0) {
    return (
      <div className="flex justify-center p-10">
        No matching tasks found.
      </div>
    );
  }

  if (props.state === 'loading') {
    return (
      <div className="flex justify-center p-10">
        Loading tasks...
      </div>
    );
  }

  if (props.state === 'error') {
    return (
      <div className="flex justify-center p-10 text-red-500">
        Error loading tasks.
      </div>
    );
  }

  if (props.state === 'success') {
    return (
      <ul className="list-none flex flex-wrap justify-center p-10">
        {tasks.map((task) => (
          <li key={task.taskIDAndDetailPageURLMus} className="bg-white shadow-md rounded py-4 px-6 mb-4 text-gray-700">
            <a href={task.taskIDAndDetailPageURLMus}>
              {task.taskTitleAndDescriptionField}
            </a>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <ul className="list-none flex flex-wrap justify-center p-10">
      {tasks.map((task) => (
        <li key={task.taskIDAndDetailPageURLMus} className="bg-white shadow-md rounded py-4 px-6 mb-4 text-gray-700">
          <a href={task.taskIDAndDetailPageURLMus}>
            {task.taskTitleAndDescriptionField}
          </a>
        </li>
      ))}
    </ul>
  );
}