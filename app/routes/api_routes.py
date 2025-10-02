"""API routes for the application."""
from flask import Blueprint, request, jsonify, current_app
import logging

logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/search', methods=['GET', 'POST'])
def search():
    """
    Search APIs endpoint.
    Updated to handle Platform array structure.
    """
    try:
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('q', '')
            page = data.get('page', 1)
            page_size = data.get('page_size', 10)
        else:
            query = request.args.get('q', '')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 10))
        
        # Validate pagination
        if page < 1:
            return jsonify({'error': 'Page must be >= 1'}), 400
        if page_size < 1 or page_size > 100:
            return jsonify({'error': 'Page size must be between 1 and 100'}), 400
        
        # Use the database service to search
        # The search_apis method now returns flattened results
        all_results = current_app.db_service.search_apis(
            query=query,
            regex=False,
            case_sensitive=False,
            limit=1000  # Get more results for pagination
        )
        
        # Calculate pagination
        total_results = len(all_results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get paginated results
        paginated_results = all_results[start_idx:end_idx]
        
        # Calculate total pages
        total_pages = (total_results + page_size - 1) // page_size
        
        return jsonify({
            'status': 'success',
            'data': paginated_results,
            'metadata': {
                'query': query,
                'page': page,
                'page_size': page_size,
                'total_results': total_results,
                'total_pages': total_pages,
                'results_in_page': len(paginated_results)
            }
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/suggestions/<field>', methods=['GET'])
def get_suggestions(field):
    """Get autocomplete suggestions for a field."""
    try:
        prefix = request.args.get('prefix', '')
        
        # Map field names to database fields (updated for Platform array)
        field_mapping = {
            'Platform': 'Platform.PlatformID',
            'Environment': 'Platform.Environment.environmentID',
            'Status': 'Platform.Environment.status',
            'UpdatedBy': 'Platform.Environment.updatedBy',
            'APIName': 'API Name'
        }
        
        db_field = field_mapping.get(field, field)
        
        # Get distinct values from database
        # Handle both old and new structure
        if field in ['Platform', 'Environment', 'Status', 'UpdatedBy']:
            # For nested fields, we need to use aggregation
            pipeline = []
            
            if field == 'Platform':
                pipeline = [
                    {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': True}},
                    {'$group': {'_id': '$Platform.PlatformID'}},
                    {'$match': {'_id': {'$regex': f'^{prefix}', '$options': 'i'}}},
                    {'$limit': 10}
                ]
            elif field in ['Environment', 'Status', 'UpdatedBy']:
                nested_field = {
                    'Environment': 'environmentID',
                    'Status': 'status',
                    'UpdatedBy': 'updatedBy'
                }[field]
                pipeline = [
                    {'$unwind': {'path': '$Platform', 'preserveNullAndEmptyArrays': True}},
                    {'$unwind': {'path': '$Platform.Environment', 'preserveNullAndEmptyArrays': True}},
                    {'$group': {'_id': f'$Platform.Environment.{nested_field}'}},
                    {'$match': {'_id': {'$regex': f'^{prefix}', '$options': 'i'}}},
                    {'$limit': 10}
                ]
            
            results = list(current_app.db_service.collection.aggregate(pipeline))
            suggestions = [r['_id'] for r in results if r['_id']]
        else:
            # For simple fields, use distinct
            all_values = current_app.db_service.collection.distinct(db_field)
            
            # Filter by prefix
            suggestions = [
                v for v in all_values 
                if v and str(v).lower().startswith(prefix.lower())
            ][:10]
        
        return jsonify({
            'status': 'success',
            'data': suggestions
        })
        
    except Exception as e:
        logger.error(f"Suggestions error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/stats', methods=['GET'])
def get_stats():
    """Get database statistics."""
    try:
        stats = current_app.db_service.get_stats()
        
        # Count total deployments (platform-environment combinations)
        pipeline = [
            {'$project': {
                'deployments': {
                    '$cond': {
                        'if': {'$isArray': '$Platform'},
                        'then': {
                            '$reduce': {
                                'input': '$Platform',
                                'initialValue': 0,
                                'in': {
                                    '$add': [
                                        '$$value',
                                        {'$cond': {
                                            'if': {'$isArray': '$$this.Environment'},
                                            'then': {'$size': '$$this.Environment'},
                                            'else': 1
                                        }}
                                    ]
                                }
                            }
                        },
                        'else': 1
                    }
                }
            }},
            {'$group': {
                '_id': None,
                'total_deployments': {'$sum': '$deployments'}
            }}
        ]
        
        deployment_result = list(current_app.db_service.collection.aggregate(pipeline))
        total_deployments = deployment_result[0]['total_deployments'] if deployment_result else 0
        
        stats['total_deployments'] = total_deployments
        
        return jsonify({
            'status': 'success',
            'data': stats
        })
        
    except Exception as e:
        logger.error(f"Stats error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/export', methods=['POST'])
def export_data():
    """
    Export search results.
    Updated to handle flattened Platform array data.
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        format_type = data.get('format', 'json')
        
        # Get search results (already flattened)
        results = current_app.db_service.search_apis(
            query=query,
            regex=False,
            case_sensitive=False,
            limit=10000
        )
        
        if format_type == 'csv':
            import csv
            import io
            
            # Create CSV
            output = io.StringIO()
            
            if results:
                # Use the keys from the first result as headers
                fieldnames = results[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                
                writer.writeheader()
                for row in results:
                    # Convert Properties dict to string for CSV
                    if 'Properties' in row:
                        row['Properties'] = str(row['Properties'])
                    writer.writerow(row)
            
            # Get CSV string
            csv_data = output.getvalue()
            
            # Return as CSV file
            response = current_app.response_class(
                csv_data,
                mimetype='text/csv',
                headers={'Content-Disposition': 'attachment; filename=api_export.csv'}
            )
            return response
            
        else:
            # Return as JSON
            return jsonify({
                'status': 'success',
                'data': results,
                'count': len(results)
            })
            
    except Exception as e:
        logger.error(f"Export error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500