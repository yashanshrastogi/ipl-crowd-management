/**
 * BentoGrid — Responsive CSS Grid layout container.
 *
 * 4-column bento pattern on desktop, 2-col on tablet, 1-col on mobile.
 * Children use helper classes: bento-item-wide, bento-item-tall, bento-item-full.
 */

export default function BentoGrid({ children, className = '' }) {
  return (
    <div className={`bento-grid ${className}`} id="dashboard-grid">
      {children}
    </div>
  );
}

/**
 * BentoItem — Individual bento cell wrapper.
 * @param {'normal'|'wide'|'tall'|'full'} span  Grid span mode
 */
export function BentoItem({ children, span = 'normal', className = '', id }) {
  const spanClass = {
    normal: '',
    wide: 'bento-item-wide',
    tall: 'bento-item-tall',
    full: 'bento-item-full',
  }[span];

  return (
    <div
      className={`glass-card bento-cell ${spanClass} ${className}`}
      id={id}
      style={{ padding: '20px', overflow: 'hidden' }}
    >
      {children}
    </div>
  );
}
