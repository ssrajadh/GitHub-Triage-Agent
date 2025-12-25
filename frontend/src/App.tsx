import { useState, useEffect } from 'react';
import Header from './components/Header';
import IssueFeed from './components/IssueFeed';
import DiffViewer from './components/DiffViewer';
import ActionPanel from './components/ActionPanel';
import { useWebSocket } from './hooks/useWebSocket';
import { AgentState } from './types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';

function App() {
  const { isConnected, latestState, reconnect } = useWebSocket(WS_URL);
  const [states, setStates] = useState<AgentState[]>([]);
  const [selectedState, setSelectedState] = useState<AgentState | null>(null);

  // Update states when new state arrives
  useEffect(() => {
    if (latestState) {
      setStates(prevStates => {
        // Check if state already exists
        const existingIndex = prevStates.findIndex(s => s.issue_id === latestState.issue_id);
        
        if (existingIndex >= 0) {
          // Update existing state
          const newStates = [...prevStates];
          newStates[existingIndex] = latestState;
          return newStates;
        } else {
          // Add new state at the beginning
          return [latestState, ...prevStates];
        }
      });

      // Update selected state if it's the same issue
      if (selectedState?.issue_id === latestState.issue_id) {
        setSelectedState(latestState);
      }
    }
  }, [latestState, selectedState?.issue_id]);

  const handleSelectIssue = (state: AgentState) => {
    setSelectedState(state);
  };

  const handleActionComplete = () => {
    // Refresh or update the state
    if (selectedState) {
      const updatedState = states.find(s => s.issue_id === selectedState.issue_id);
      if (updatedState) {
        setSelectedState(updatedState);
      }
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      <Header isConnected={isConnected} onReconnect={reconnect} />
      
      <div className="flex-1 flex overflow-hidden">
        {/* Issue Feed - Left Sidebar */}
        <div className="w-96 border-r bg-white shadow-sm overflow-hidden">
          <IssueFeed
            states={states}
            onSelectIssue={handleSelectIssue}
            selectedIssueId={selectedState?.issue_id}
          />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Diff Viewer - Top */}
          <div className="flex-1 overflow-hidden">
            <DiffViewer state={selectedState} />
          </div>

          {/* Action Panel - Bottom */}
          <div className="h-auto border-t shadow-lg">
            <ActionPanel
              state={selectedState}
              onActionComplete={handleActionComplete}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
