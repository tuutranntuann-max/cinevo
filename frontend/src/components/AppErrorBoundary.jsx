import { Component } from "react";

export default class AppErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("CINEVO encountered a rendering error.", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="app-error-page" role="alert">
          <section className="app-error-card">
            <p className="eyebrow">CINEVO</p>
            <h1>Không thể hiển thị trang này</h1>
            <p>Đã xảy ra lỗi khi tải giao diện. Bạn có thể thử tải lại trang hoặc quay về trang chủ.</p>
            <div className="actions">
              <button className="btn btn-red" type="button" onClick={() => window.location.reload()}>
                Tải lại trang
              </button>
              <a className="btn btn-outline" href="/user">Về trang chủ</a>
            </div>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}
