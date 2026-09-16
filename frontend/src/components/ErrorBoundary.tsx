import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  fallbackMessage?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an unhandled error:', error, errorInfo);
  }

  public handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-6 rounded-2xl bg-amber-50 border-2 border-amber-300 text-amber-950 shadow-sm space-y-4 my-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-1">
              <h4 className="text-sm font-black uppercase tracking-wider">
                {this.props.fallbackTitle || 'Section Display Error'}
              </h4>
              <p className="text-xs text-amber-800">
                {this.props.fallbackMessage || 'A rendering error occurred while displaying this section. The rest of the application remains fully functional.'}
              </p>
              {this.state.error && (
                <p className="text-[11px] font-mono text-amber-900 bg-amber-100/70 p-2 rounded border border-amber-200 mt-2">
                  {this.state.error.message}
                </p>
              )}
            </div>
          </div>
          <div>
            <button
              type="button"
              onClick={this.handleReset}
              className="px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 text-white text-xs font-bold rounded-xl shadow-xs inline-flex items-center gap-1.5 cursor-pointer transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Retry / Reset Section</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
