import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { Dashboard } from "./pages/Dashboard";
import { BotManagement } from "./pages/BotManagement";
import { AgentManagement } from "./pages/AgentManagement";
import { UsageAnalytics } from "./pages/UsageAnalytics";
import { QueueMonitor } from "./pages/QueueMonitor";
import { Login } from "./pages/Login";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Toaster } from "@/components/ui/toaster";

// Create a client
const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-background">
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/bots"
              element={
                <ProtectedRoute>
                  <BotManagement />
                </ProtectedRoute>
              }
            />
            <Route
              path="/agents"
              element={
                <ProtectedRoute>
                  <AgentManagement />
                </ProtectedRoute>
              }
            />
            <Route
              path="/usage"
              element={
                <ProtectedRoute>
                  <UsageAnalytics />
                </ProtectedRoute>
              }
            />
            <Route
              path="/queues"
              element={
                <ProtectedRoute>
                  <QueueMonitor />
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </Router>
      <Toaster />
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
}

export default App;
