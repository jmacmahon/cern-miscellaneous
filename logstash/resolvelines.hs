import Network.Socket ( inet_ntoa, HostAddress )
import Network.BSD ( getHostByName, hostAddresses, HostEntry )
import Control.Exception ( try, IOException )
import Data.Maybe ( fromMaybe, fromJust, isNothing )
import Control.Monad ( join, mapM )
import System.IO ( stdin, stdout, Handle, hIsEOF, hGetLine, hPutStrLn )
import qualified Data.Map as M
import Control.Monad.Trans.State ( StateT, runStateT, get, modify )
import Control.Monad.IO.Class ( liftIO, MonadIO )

eitherToMaybe :: Either a b -> Maybe b
eitherToMaybe (Left  _) = Nothing
eitherToMaybe (Right a) = Just a

flipIOMaybe :: Maybe (IO a) -> IO (Maybe a)
flipIOMaybe m = fromMaybe (return Nothing) $ (fmap (fmap Just)) m

resolve :: String -> IO (Maybe [String])
resolve host = do eitherEntry <- ((try $ getHostByName host) :: IO (Either IOException HostEntry))
                  let maybeEntry = eitherToMaybe eitherEntry
                      maybeAddresses :: Maybe (IO [String])
                      maybeAddresses = do entry <- maybeEntry
                                          let addresses = hostAddresses entry
                                              addressStrings = mapM inet_ntoa addresses
                                          return addressStrings
                  flipIOMaybe maybeAddresses

type Cache = M.Map String String
type Resolver = StateT Cache IO

getOneAddress :: String -> Resolver String
getOneAddress host = let resolve' :: IO String
                         resolve' = do maybeAddresses <- resolve host
                                       return $ fromMaybe "0.0.0.0" (fmap head maybeAddresses)
                         resolveAndCache :: Resolver String
                         resolveAndCache = do addr <- liftIO resolve'
                                              modify (M.insert host addr)
                                              return addr
                     in do cache <- get
                           fromMaybe resolveAndCache $ fmap return $ M.lookup host cache

whileNotEOF :: MonadIO m => (String -> m String) -> (Handle, Handle) -> m ()
whileNotEOF f (inp, out) = do eof <- liftIO $ hIsEOF inp
                              if eof
                                then return ()
                                else do inLine <- liftIO $ hGetLine inp
                                        outLine <- f inLine
                                        liftIO $ hPutStrLn out outLine
                                        whileNotEOF f (inp, out)

processLine :: String -> Resolver String
processLine line = let ws = words line
                       processWords [] = return ""
                       processWords (host:ws) = do address <- getOneAddress host
                                                   let outLine = (address:ws)
                                                   return $ unwords outLine
                   in processWords ws

main :: IO ()
main = fmap fst (runStateT (whileNotEOF processLine (stdin, stdout)) M.empty)
