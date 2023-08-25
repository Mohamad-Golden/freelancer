import "@/styles/globals.css";
import { createTheme, ThemeProvider } from '@mui/material/styles';
export default function App({ Component, pageProps }) {
    return (
        // <ThemeProvider theme={createTheme()}>
            <Component {...pageProps} />
        // </ThemeProvider>
    );
}
