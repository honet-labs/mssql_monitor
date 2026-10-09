"""Microsoft SQL Server via pyodbc; one login per Discovery execution."""
OS_NAME='MSSQL'

def connect(cfg):
    try:import pyodbc
    except ImportError as e:raise RuntimeError('Install Python package pyodbc and an ODBC Driver for SQL Server on the Pandora server') from e
    driver=cfg.get('driver','ODBC Driver 18 for SQL Server')
    allowed=['ODBC Driver 18 for SQL Server','ODBC Driver 17 for SQL Server','FreeTDS']
    if driver not in allowed:raise ValueError('Unsupported ODBC driver selection')
    if driver not in pyodbc.drivers():raise RuntimeError('ODBC driver not installed: '+driver+'; available: '+', '.join(pyodbc.drivers()))
    def q(s):return '{'+str(s).replace('}','}}')+'}'
    host=cfg.get('host','')
    port=int(cfg.get('port') or 1433)
    if port<1 or port>65535:raise ValueError('Invalid SQL Server TCP port')
    encrypt='yes' if cfg.get('encrypt','true').lower() in ('1','true','yes','on') else 'no'
    trust='yes' if cfg.get('trust_server_cert','false').lower() in ('1','true','yes','on') else 'no'
    # Whitelist connection attributes, never accept an arbitrary freeform connection string.
    connstr=';'.join(['DRIVER='+q(driver),'SERVER='+q(host+','+str(port)),
                     'DATABASE='+q(cfg.get('database','master')), 'UID='+q(cfg.get('user','')),
                     'PWD='+q(cfg.get('password','')),'Encrypt='+encrypt,'TrustServerCertificate='+trust,
                     'APP='+q('PandoraFMS-MSSQL-Discovery')])+';'
    conn=pyodbc.connect(connstr,timeout=int(cfg.get('connect_timeout') or 10),autocommit=True)
    return conn

def init_session(conn,cursor,cfg):
    cursor.timeout=max(1,int(int(cfg.get('statement_timeout_ms') or 15000)/1000))
    cursor.execute('SET NOCOUNT ON')
    cursor.execute('SET LOCK_TIMEOUT '+str(max(1,int(cfg.get('lock_timeout_ms') or 3000))))

def before_query(conn,cursor,cfg):pass

def on_query_error(conn,cursor,cfg):pass
