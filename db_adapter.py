"""Microsoft SQL Server via pyodbc; one login per Discovery execution."""
OS_NAME='MSSQL'
VERSION_SQL="SELECT CAST(SERVERPROPERTY('ProductVersion') AS NVARCHAR(128)), CAST(SERVERPROPERTY('Edition') AS NVARCHAR(256))"

def format_product_identity(product_version, edition):
    version=str(product_version or '').strip()
    edition=' '.join(str(edition or '').split())
    major=version.split('.',1)[0]
    # Microsoft SQL Server versions and corresponding marketing release years.
    release={'17':'2025','16':'2022','15':'2019','14':'2017','13':'2016','12':'2014','11':'2012'}.get(major)
    if 'azure sql' in edition.lower() or edition.lower().startswith('sql azure'):
        label='Azure SQL Database'
    else:
        label='Microsoft SQL Server'+(' '+release if release else '')
    return ((f'{label} ({version})' if version else label)+(' - '+edition if edition else ''))[:128]

def get_version_info(conn,cursor):
    cursor.execute(VERSION_SQL)
    row=cursor.fetchone()
    return format_product_identity(row[0],row[1] if row and len(row)>1 else '') if row else ''


def tls_parameters(cfg):
    """Resolve TLS configuration explicitly, without implicit insecure fallback.

    Existing Discovery tasks can keep using the Encrypt/Trust checkboxes
    (tls_mode=custom). The other modes are deliberate opt-ins.
    """
    mode=str(cfg.get('tls_mode') or 'custom').strip().lower()
    if mode=='custom':
        encrypt='yes' if str(cfg.get('encrypt','true')).strip().lower() in ('1','true','yes','on') else 'no'
        trust='yes' if str(cfg.get('trust_server_cert','false')).strip().lower() in ('1','true','yes','on') else 'no'
    elif mode=='verify':
        encrypt,trust='yes','no'
    elif mode=='trust':
        encrypt,trust='yes','yes'
    elif mode=='legacy':
        # Driver negotiates optional encryption; SQL Server may still force TLS.
        encrypt,trust='no','yes'
    else:
        raise ValueError('Invalid TLS Connection Mode; select a listed mode')
    return encrypt,trust


def connect(cfg):
    try:
        import pyodbc
    except ImportError as e:
        raise RuntimeError('Install pyodbc and a SQL Server ODBC driver on the Pandora Discovery server') from e
    driver=str(cfg.get('driver') or 'ODBC Driver 18 for SQL Server').strip()
    allowed=('ODBC Driver 18 for SQL Server','ODBC Driver 17 for SQL Server','FreeTDS')
    if driver not in allowed:
        raise ValueError('Unsupported ODBC driver selection')
    installed=pyodbc.drivers()
    if driver not in installed:
        raise RuntimeError('ODBC driver not installed: '+driver+'; available: '+', '.join(installed))
    def q(s):
        return '{'+str(s).replace('}','}}')+'}'
    host=str(cfg.get('host','')).strip()
    port=int(cfg.get('port') or 1433)
    if not host:
        raise ValueError('SQL Server host/IP cannot be empty')
    if port<1 or port>65535:
        raise ValueError('Invalid SQL Server TCP port')
    encrypt,trust=tls_parameters(cfg)
    # No certificate checks or encryption options are silently relaxed on error.
    # Whitelist connection attributes; credentials are not logged or returned.
    connstr=';'.join([
        'DRIVER='+q(driver),
        'SERVER='+q(host+','+str(port)),
        'DATABASE='+q(cfg.get('database','master')),
        'UID='+q(cfg.get('user','')),
        'PWD='+q(cfg.get('password','')),
        'Encrypt='+encrypt,
        'TrustServerCertificate='+trust,
        'APP='+q('PandoraFMS-MSSQL-Discovery'),
    ])+';'
    return pyodbc.connect(connstr,timeout=int(cfg.get('connect_timeout') or 10),autocommit=True)


def init_session(conn,cursor,cfg):
    cursor.timeout=max(1,int(int(cfg.get('statement_timeout_ms') or 15000)/1000))
    cursor.execute('SET NOCOUNT ON')
    cursor.execute('SET LOCK_TIMEOUT '+str(max(1,int(cfg.get('lock_timeout_ms') or 3000))))

def before_query(conn,cursor,cfg):pass

def on_query_error(conn,cursor,cfg):pass
