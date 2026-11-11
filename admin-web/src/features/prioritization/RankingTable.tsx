import type { MouseEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ReviewRoadChip } from "../../components/ReviewRoadChip";
import { SeverityChip } from "../../components/SeverityChip";
import { StatusChip } from "../../components/StatusChip";
import { formatScore, formatShortDate } from "../../format/format";
import type { RankingItem } from "./api";

function confirmationsLabel(count: number): string {
  return count === 1 ? "1 confirmación" : `${count} confirmaciones`;
}

type Props = {
  items: readonly RankingItem[];
  /** Posición del primer elemento de la página, desde 0. */
  offset: number;
};

/** Ranking en el orden que da la API; el panel no reordena ni calcula (guía 10.4). */
export function RankingTable({ items, offset }: Props) {
  const navigate = useNavigate();

  function openDetail(event: MouseEvent<HTMLTableRowElement>, id: string) {
    // El enlace de la fila ya navega por su cuenta (y es el camino del teclado).
    if (event.target instanceof Element && event.target.closest("a")) {
      return;
    }
    navigate(`/reportes/${id}`);
  }

  return (
    <table className="ranking">
      <thead>
        <tr>
          <th scope="col" className="ranking__position">
            <abbr title="Posición">#</abbr>
          </th>
          <th scope="col">Reporte</th>
          <th scope="col" className="ranking__number">
            <abbr title="Severidad">S</abbr>
          </th>
          <th scope="col" className="ranking__number">
            <abbr title="Flujo vehicular">F</abbr>
          </th>
          <th scope="col" className="ranking__number">
            <abbr title="Proximidad a servicios críticos">P</abbr>
          </th>
          <th scope="col" className="ranking__number">
            <abbr title="Urgencia">U</abbr>
          </th>
        </tr>
      </thead>
      <tbody>
        {items.map((item, index) => (
          <tr key={item.id} onClick={(event) => openDetail(event, item.id)}>
            <td className="ranking__position">
              <span className="ranking__badge">{offset + index + 1}</span>
            </td>
            <td>
              <Link to={`/reportes/${item.id}`} className="ranking__address">
                {item.address}
              </Link>
              <div className="ranking__meta">
                <StatusChip status={item.status} />
                <SeverityChip severity={item.severity} />
                {item.needs_road_review ? <ReviewRoadChip /> : null}
                <span>{confirmationsLabel(item.confirmations)}</span>
                <span>{formatShortDate(item.created_at)}</span>
              </div>
            </td>
            <td className="ranking__number">{formatScore(item.s)}</td>
            <td className="ranking__number">{formatScore(item.f)}</td>
            <td className="ranking__number">{formatScore(item.p)}</td>
            <td className="ranking__number ranking__score">{formatScore(item.u)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
