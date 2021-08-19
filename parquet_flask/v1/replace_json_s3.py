import logging

from flask_restx import Resource, Namespace, fields
from flask import request

from parquet_flask.aws.aws_s3 import AwsS3
from parquet_flask.io_logic.cdms_constants import CDMSConstants
from parquet_flask.io_logic.metadata_tbl_io import MetadataTblIO
from parquet_flask.io_logic.replace_file import ReplaceJsonFile
from parquet_flask.utils.file_utils import FileUtils
from parquet_flask.utils.general_utils import GeneralUtils
from parquet_flask.utils.time_utils import TimeUtils

api = Namespace('replace_json_s3', description="Ingesting JSON files")
LOGGER = logging.getLogger(__name__)

query_model = api.model('replace_json_s3', {
    's3_url': fields.String(required=True, example='s3://<bucket>/<key>'),
    'job_id': fields.String(required=True, example='sample-uuid'),
})

_QUERY_SCHEMA = {
    'type': 'object',
    'properties': {
        's3_url': {'type': 'string'},
        'job_id': {'type': 'string'},
    },
    'required': ['s3_url', 'job_id'],
}


@api.route('', methods=["put"])
class IngestParquet(Resource):
    def __init__(self, api=None, *args, **kwargs):
        super().__init__(api, args, kwargs)
        self.__saved_dir = '/tmp'  # TODO update this

    @api.expect(fields=query_model)
    def put(self):
        """
        s3://ecsv-h5-data-v1/INDEX/GALILEO/filenames.txt.gz

        :return:
        """
        payload = request.get_json()
        is_valid, json_error = GeneralUtils.is_json_valid(payload, _QUERY_SCHEMA)
        if not is_valid:
            return {'message': 'invalid request body', 'details': str(json_error)}, 400
        try:
            s3 = AwsS3().set_s3_url(payload['s3_url'])
            job_id = payload['job_id']
            saved_file_name = s3.download(payload['s3_url'], self.__saved_dir)
            if saved_file_name.lower().endswith('.gz'):
                LOGGER.debug(f's3 file is in gzipped form. unzipping. {saved_file_name}')
                saved_file_name = FileUtils.gunzip_file_os(saved_file_name)
            LOGGER.debug(f'ingesting file: {saved_file_name}')
            start_time = TimeUtils.get_current_time_unix()
            num_records = ReplaceJsonFile().ingest(saved_file_name, job_id)
            end_time = TimeUtils.get_current_time_unix()
            LOGGER.debug(f'uploading to metadata table')
            db_io = MetadataTblIO()
            db_io.insert_record({
                CDMSConstants.s3_url_key: payload['s3_url'],
                CDMSConstants.uuid_key: job_id,
                CDMSConstants.ingested_date_key: TimeUtils.get_current_time_unix(),
                CDMSConstants.file_size_key: FileUtils.get_size(saved_file_name),
                CDMSConstants.checksum_key: FileUtils.get_checksum(saved_file_name),
                CDMSConstants.job_start_key: start_time,
                CDMSConstants.job_end_key: end_time,
                CDMSConstants.records_count_key: num_records,
            })
            LOGGER.debug(f'deleting used file')
            FileUtils.del_file(saved_file_name)
            # TODO make it background process?
            s3.add_tags_to_obj({
                'parquet_ingested': TimeUtils.get_current_time_str(),
                'job_id': job_id,
            })
            return {'message': 'ingested'}, 201
        except Exception as e:
            return {'message': 'failed to ingest to parquet', 'details': str(e)}, 500
