export default function ErrorBox({ message }) {
  return message ? <div className="alert" role="alert">{message}</div> : null;
}
