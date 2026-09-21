import { Component } from "react";

/** U-04 (audit 2026-09-02) — satu baris rusak tidak boleh mematikan seluruh SPA. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div data-testid="view-error-boundary" className="m-6 rounded-lg border border-[#F2C4C4] bg-[#FFF5F5] p-5">
        <p className="text-[14px] font-bold text-[#B42318]">Layar ini gagal ditampilkan</p>
        <p className="mt-1 text-[12.5px] text-[#3C3C43]">
          Terjadi kesalahan saat merender halaman. Menu lain tetap bisa dipakai — pindah halaman atau coba lagi.
        </p>
        <p data-testid="view-error-message" className="mt-2 break-all font-mono text-[11px] text-[#6B6B73]">
          {String(this.state.error?.message || this.state.error)}
        </p>
        <button
          type="button"
          data-testid="view-error-retry"
          className="secondary-button mt-3"
          onClick={() => this.setState({ error: null })}
        >
          Coba lagi
        </button>
      </div>
    );
  }
}
