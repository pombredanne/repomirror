
__all__ = [ 'MirrorRepository' , 'MirrorComponent' , 'BuildRepository' ]

import os
import tempfile
import shutil , errno

import urllib2


import repolib
import utils
from lists import *

class _repository :

    def new ( name ) :
        raise Exception( "Calling an abstract method" )

    def __init__ ( self , config ) :

        self.name = config.name

	self.destdir = config[ "destdir" ]
        self.version = config[ "version" ]

        self.architectures = config[ "architectures" ]

        if not os.path.isdir( self.destdir ) :
            raise Exception( "Destination directory %s does not exists" % self.destdir )

    def repo_path ( self ) :
        raise Exception( "Calling an abstract method" )


class _mirror ( _repository ) :
    """Convenience class primarily created only to avoid moving download method into base _repository"""

    def __init__ ( self , config ) :
	_repository.__init__( self , config )
        self.repo_url = config[ "url" ]
        self.mode = config[ "mode" ]
        self.params = config[ "params" ]
        self.filters = config[ "filters" ]

    def metadata_path ( self , partial=False ) :
        raise Exception( "Calling an abstract method" )

    def downloadRawFile ( self , remote , local=None ) :
        """Downloads a remote file to the local system.

        remote - path relative to repository base
        local - Optional local name for the file

        Returns the local file name or False if errors"""

        remote = utils.urljoin( self.repo_url , remote ) 

        if not local :
            (handle, fname) = tempfile.mkstemp()
        else :
            fname = local
            handle = os.open( fname , os.O_WRONLY | os.O_TRUNC | os.O_CREAT )
        try:
            response = urllib2.urlopen( remote )
            data = response.read(256)
            while data :
                os.write(handle, data)
                data = response.read(256)
            os.close(handle)
        except Exception ,ex :
            repolib.logger.error( "Exception : %s" % ex )
            os.close(handle)
            os.unlink(fname)
            return False
        return fname

class MirrorRepository ( _mirror ) :

    def new ( name ) :
        _config = repolib.config.read_mirror_config( name )
        if _config['type'] == "yum" :
            return repolib.yum_repository( _config )
        elif _config['type'] == "fedora" :
            return repolib.fedora_repository( _config )
        elif _config['type'] == "centos" :
            return repolib.centos_repository( _config )
        elif _config['type'] == "fedora_upd" :
            return repolib.fedora_update_repository( _config )
        elif _config['type'] == "centos_upd" :
            return repolib.centos_update_repository( _config )
        elif _config['type'] == "deb" :
            return repolib.debian_repository( _config )
        elif _config['type'] == "feed" :
            return repolib.feed_repository( _config )
        else :
            raise Exception( "Unknown repository type '%s'" % _config['type'] )
    new = staticmethod( new )

    def __init__ ( self , config ) :
	_mirror.__init__( self , config )
        self.subrepos = []

    def get_master_file ( self , params , keep=False ) :
        raise Exception( "Calling an abstract method" )

    def get_signed_metafile ( self , params , meta_file , sign_ext=None , keep=False ) :
        """
Verifies with gpg and/or downloads a metadata file. Return the full pathname
of metadata file on success and False if any error occur. In the signature
verification is not successfull, the local copy is removed and the file is
dowloaded into a temporary location. This behaviour can be disabled by setting
the keep option, and is usually done to avoid the break of already downloaded
repositories.

The returned file is always and off-tree temporary one except when the file
did already exists and signature was successfully verified. When working on
update mode, the special value True is returned to signal that no further
processing is required
"""

        release_file = os.path.join( self.repo_path() , meta_file )

        if params['usegpg'] and sign_ext :

            signature_file = self.downloadRawFile( meta_file + sign_ext )

            if not signature_file :
                repolib.logger.error( "Signature file for version '%s' not found." % ( self.version ) )
                return False

            if os.path.isfile( release_file ) :
                if not utils.gpg_verify( signature_file , release_file , repolib.logger.warning ) :
                    # NOTE : The keep flag is a different approach to the behaviour wanted by update mode
                    if keep :
                        release_file = ""
                    else :
                        os.unlink( release_file )
                        os.unlink( release_file + sign_ext )
                else :
                    if self.mode == "update" :
                        repolib.logger.info( "Existing metadata file is valid, skipping" )
                        os.unlink( signature_file )
                        return True

        else :
            # If gpg is not enabled, the metafile is removed to force fresh download
            if os.path.isfile( release_file ) :
                if keep :
                    release_file = ""
                else :
                    os.unlink( release_file )

        if not os.path.isfile( release_file ) :

            release_file = self.downloadRawFile( meta_file )

            if release_file :
                if params['usegpg'] and sign_ext :
                    if not utils.gpg_verify( signature_file , release_file , repolib.logger.error ) :
                        repolib.logger.error( errstr )
                        os.unlink( release_file )
                        release_file = False

        if params['usegpg'] and sign_ext :
          if isinstance(release_file,str) :
            self.safe_rename( signature_file , release_file + sign_ext )
          else :
            os.unlink( signature_file )

        return release_file

    def safe_rename ( self , src , dst ) :
        try :
            os.rename( src , dst )
        except OSError , ex :
            if ex.errno != errno.EXDEV :
                repolib.logger.critical( "OSError: %s" % ex )
                sys.exit(1)
            shutil.move( src , dst )

    def info ( self , release_file ) :
        raise Exception( "Calling an abstract method" )

    def write_master_file ( self , release_file ) :
        raise Exception( "Calling an abstract method" )

    def build_local_tree( self ) :

        for subrepo in self.subrepos :
            packages_path = os.path.join( subrepo.repo_path() , subrepo.metadata_path() )
            if not os.path.exists( packages_path ) :
                os.makedirs( packages_path )

    def get_download_list( self ) :
        return DownloadThread( self )


class MirrorComponent ( _mirror ) :

    def __init__ ( self , config , compname ) :
        _mirror.__init__( self , config )
        self.architectures = [ compname ]

    def __str__ ( self ) :
        return "%s" % self.architectures[0]

    def __hash__ ( self ) :
        return hash(str(self))

    def get_metafile( self , metafile , _params , download=True ) :
        raise Exception( "Calling an abstract method" )

    def match_filters( self , pkginfo , filters ) :
        raise Exception( "Calling an abstract method" )

    def get_package_list ( self , fd , _params , filters ) :
        raise Exception( "Calling an abstract method" )

    def verify( self , filename , _name , release , params ) :
        raise Exception( "Calling an abstract method" )

    def pkg_list( self ) :
        return PackageList()


class BuildRepository ( _repository ) :

    def new ( name ) :
        _config = repolib.config.read_build_config( name )
        if _config['type'] == "deb" :
            return repolib.debian_build_repository( _config )
        elif _config['type'] == "feed" :
            return repolib.feed_build_repository( _config , name )
        else :
            raise Exception( "Unknown repository build type '%s'" % _config['type'] )
    new = staticmethod( new )
