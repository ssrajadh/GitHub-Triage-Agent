import React from 'react';
import { Bot, Wifi, WifiOff, RefreshCw } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
  onReconnect: () => void;
}

const Header: React.FC<HeaderProps> = ({ isConnected, onReconnect }) => {
  return (
    <header className="bg-gradient-to-r from-blue-600 to-blue-800 text-white shadow-lg">
      <div className="px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bot className="w-8 h-8" />
            <div>
              <h1 className="text-2xl font-bold">GitHub Triage Agent</h1>
              <p className="text-blue-100 text-sm">Mission Control Dashboard</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              {isConnected ? (
                <>
                  <Wifi className="w-5 h-5 text-green-300" />
                  <span className="text-sm font-medium">Connected</span>
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
                </>
              ) : (
                <>
                  <WifiOff className="w-5 h-5 text-red-300" />
                  <span className="text-sm font-medium">Disconnected</span>
                  <button
                    onClick={onReconnect}
                    className="ml-2 px-3 py-1 bg-white/20 hover:bg-white/30 rounded-lg text-sm flex items-center gap-1 transition-colors"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Reconnect
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
