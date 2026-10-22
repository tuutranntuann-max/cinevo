import ResourcePage from "../../components/ResourcePage";
import { formatVND } from "../../utils/format";

const columns = [{ key: "id", label: "ID" }, { key: "name", label: "Tên" }, { key: "description", label: "Mô tả" }, { key: "price", label: "Giá", render: (r) => formatVND(r.price) }];

export default function FoodManagement() {
  return <ResourcePage title="Quản lý đồ ăn" endpoint="/manager/foods" columns={columns} />;
}
