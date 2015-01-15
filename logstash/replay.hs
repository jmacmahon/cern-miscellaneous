import System.IO

main :: IO ()
main = do h <- openFile "logs/apache.log" ReadMode
          hSetBuffering stdout LineBuffering
          hSetBuffering stderr LineBuffering
          playLines h

playLines :: Handle -> IO ()
playLines h = do eof <- hIsEOF h
                 if eof
                   then return ()
                   else do _ <- getLine
                           line <- hGetLine h
                           hPutStrLn stderr line
                           hPutStrLn stdout line
                           playLines h
