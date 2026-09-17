import { action } from '../overlay/bridge';
export function Interaction() { return <div className="interaction"><strong>PIP</strong>{['Battle','Capture','Close'].map(label => <button key={label} onClick={() => void action(label.toLowerCase())}>{label}</button>)}</div>; }
