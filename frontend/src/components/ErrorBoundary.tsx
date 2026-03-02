import React, { type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          className="flex h-screen items-center justify-center"
          style={{ backgroundColor: "#1a1f36" }}
        >
          <div className="text-center">
            <p className="text-base font-semibold" style={{ color: "#0ea5e9" }}>
              Something went wrong.
            </p>
            <p className="mt-1 text-sm" style={{ color: "#64748b" }}>
              Refresh to try again.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
