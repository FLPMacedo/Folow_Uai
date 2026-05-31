interface Props { message: string | null; onClose?: () => void }

export default function ErrorBanner({ message, onClose }: Props) {
  if (!message) return null;
  return (
    <div className="card" style={{ background: "#fee2e2", borderColor: "#fca5a5", color: "#991b1b" }}>
      <div className="row">
        <strong>Erro:</strong>
        <span>{message}</span>
        <span className="spacer" />
        {onClose && <button className="btn" onClick={onClose}>×</button>}
      </div>
    </div>
  );
}
