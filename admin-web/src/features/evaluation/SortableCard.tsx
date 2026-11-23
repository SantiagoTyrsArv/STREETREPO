import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { AuthImage } from "../../components/AuthImage";
import { SeverityChip } from "../../components/SeverityChip";
import { photoPath, type BlindCard } from "./api";
import { cardLabel } from "./labels";

type Props = {
  card: BlindCard;
  position: number;
  total: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onShowMap: () => void;
};

/** Tarjeta de la vista a ciegas: solo foto, vía, severidad declarada y descripción. */
export function SortableCard({ card, position, total, onMoveUp, onMoveDown, onShowMap }: Props) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.report_id });
  const label = cardLabel(card);

  return (
    <li
      ref={setNodeRef}
      className={`card blind-card${isDragging ? " blind-card--dragging" : ""}`}
      style={{ transform: CSS.Transform.toString(transform), transition }}
    >
      <span className="blind-card__position" aria-hidden="true">
        {position}
      </span>
      <AuthImage
        src={photoPath(card.report_id, "thumbnail")}
        alt={`Foto del daño en ${label}`}
        className="blind-card__photo"
      />
      <div className="blind-card__text">
        <h2 className="blind-card__road">{label}</h2>
        <SeverityChip severity={card.severity} />
        {card.description ? <p className="blind-card__description">{card.description}</p> : null}
        <button
          type="button"
          className="blind-card__map-link"
          onClick={onShowMap}
          aria-label={`Ver en el mapa ${label}`}
        >
          Ver en el mapa
        </button>
      </div>
      <div className="blind-card__actions">
        <button
          type="button"
          className="button button--secondary blind-card__move"
          onClick={onMoveUp}
          disabled={position === 1}
          aria-label={`Subir ${label}`}
        >
          ▲
        </button>
        <button
          type="button"
          className="button button--secondary blind-card__move"
          onClick={onMoveDown}
          disabled={position === total}
          aria-label={`Bajar ${label}`}
        >
          ▼
        </button>
        <button
          type="button"
          ref={setActivatorNodeRef}
          className="button button--secondary blind-card__move blind-card__handle"
          aria-label={`Arrastrar ${label}`}
          {...attributes}
          {...listeners}
        >
          ⠿
        </button>
      </div>
    </li>
  );
}
