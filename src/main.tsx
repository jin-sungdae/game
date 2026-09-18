import { createRoot } from 'react-dom/client';
import { useEntities, connect } from './stores/entities';
import { Creature } from './components/Creature';
import { Interaction } from './components/Interaction';
import './style.css';
import './presentation/gameplay.css';
import './presentation/baseMotion.css';
const kind = new URLSearchParams(location.search).get('entity') ?? 'moa';
function App() {
  const world = useEntities();
  if(kind === 'interaction') return <Interaction/>;
  const entity = kind === 'pip' ? world.pip : world.moa;
  return entity ? <Creature kind={kind === 'pip' ? 'pip':'moa'} entity={entity}/> : null;
}
connect().then(stop => window.addEventListener('beforeunload', stop, { once:true })).catch(console.error);
createRoot(document.getElementById('root')!).render(<App/>);
