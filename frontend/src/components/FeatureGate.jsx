// Chặn route của tính năng đang tắt: tắt thì chuyển về trang fallback.
import { Navigate } from "react-router-dom";
import { useFeatures } from "../context/FeaturesContext";
import Loading from "./Loading";

export default function FeatureGate({ feature, fallback = "/", children }) {
  const { features, loaded } = useFeatures();
  if (!loaded) return <Loading />;
  return features[feature] ? children : <Navigate to={fallback} replace />;
}
