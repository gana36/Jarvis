import PushToTalk from './components/PushToTalk';

function App() {
    return (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            gap: '16px'
        }}>
            <h1>Mini Jarvis</h1>
            <PushToTalk />
        </div>
    );
}

export default App;
