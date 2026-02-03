export function Chat() {
  return (
    <div className="flex h-[calc(100vh-57px)]">
      {/* Sidebar placeholder */}
      <div className="w-64 bg-gray-100 border-r border-gray-200 p-4">
        <button className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Chat
        </button>
        <div className="mt-4 text-sm text-gray-500">
          Conversations will appear here
        </div>
      </div>

      {/* Chat area placeholder */}
      <div className="flex-1 flex flex-col items-center justify-center">
        <h2 className="text-2xl font-semibold text-gray-700">
          Welcome to Nebulus Gantry
        </h2>
        <p className="mt-2 text-gray-500">
          Start a new conversation or select an existing one
        </p>
      </div>
    </div>
  );
}
