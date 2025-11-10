"""API routes for the application."""
from flask import Blueprint, request, jsonify, current_app
import logging
from app.utils.auth import require_auth

logger = logging.getLogger(__name__)

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/search', methods=['GET', 'POST'])
def search():
    """
    Search APIs endpoint with row-level filtering.
    Returns only matching deployment rows.
    """
    try:
        if request.method == 'POST':
            data = request.get_json()
            query = data.get('q', '')
            page = data.get('page', 1)
            page_size = data.get('page_size', 100)
        else:
            query = request.args.get('q', '')
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 100))
        
        # Validate pagination
        if page < 1:
            return jsonify({
                'status': 'error',
                'message': 'Page must be >= 1'
            }), 400
        if page_size < 1 or page_size > 1000:
            return jsonify({
                'status': 'error',
                'message': 'Page size must be between 1 and 1000'
            }), 400
        
        logger.info(f"Search request: query='{query}', page={page}, page_size={page_size}")
        
        # Search using database service (returns already flattened and filtered rows)
        all_results = current_app.db_service.search_apis(
            query=query,
            limit=10000  # Get more results for pagination
        )
        
        # Calculate pagination
        total_results = len(all_results)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        # Get paginated results
        paginated_results = all_results[start_idx:end_idx]
        
        # Calculate total pages
        total_pages = (total_results + page_size - 1) // page_size if page_size > 0 else 1
        
        logger.info(f"Search complete: {total_results} total results, returning page {page}/{total_pages}")
        
        return jsonify({
            'status': 'success',
            'data': paginated_results,
            'metadata': {
                'query': query,
                'page': page,
                'page_size': page_size,
                'total': total_results,  # ✅ FIXED: Changed from 'total_results' to 'total'
                'total_pages': total_pages,
                'results_in_page': len(paginated_results)
            }
        })
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/suggestions/<field>', methods=['GET'])
def get_suggestions(field):
    """Get autocomplete suggestions for a field."""
    try:
        prefix = request.args.get('prefix', '')
        
        # Use aggregation to get distinct values after unwinding
        if field in ['Platform', 'Environment', 'Status', 'UpdatedBy', 'Version']:
            pipeline = [
                {'$unwind': '$Platform'},
                {'$unwind': '$Platform.Environment'}
            ]
            
            field_mapping = {
                'Platform': '$Platform.PlatformID',
                'Environment': '$Platform.Environment.environmentID',
                'Status': '$Platform.Environment.status',
                'UpdatedBy': '$Platform.Environment.updatedBy',
                'Version': '$Platform.Environment.version'
            }
            
            field_path = field_mapping.get(field)
            
            pipeline.extend([
                {'$group': {'_id': field_path}},
                {'$match': {'_id': {'$regex': f'^{prefix}', '$options': 'i'}}},
                {'$limit': 10},
                {'$sort': {'_id': 1}}
            ])
            
            results = list(current_app.db_service.collection.aggregate(pipeline))
            suggestions = [r['_id'] for r in results if r['_id']]
        else:
            # For API Name
            all_values = current_app.db_service.collection.distinct('_id')
            suggestions = [
                v for v in all_values 
                if v and str(v).lower().startswith(prefix.lower())
            ][:10]
        
        return jsonify({
            'status': 'success',
            'data': sorted(suggestions)
        })
        
    except Exception as e:
        logger.error(f"Suggestions error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@bp.route('/stats', methods=['GET'])
def get_stats():
    """Get database statistics."""
    try:
        stats = current_app.db_service.get_stats()
        
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
@require_auth()
def export_data():
    """Export search results."""
    try:
        data = request.get_json()
        query = data.get('query', '')
        format_type = data.get('format', 'json')
        
        # ✅ FIXED: Validate format parameter
        valid_formats = ['json', 'csv']
        if format_type not in valid_formats:
            return jsonify({
                'status': 'error',
                'message': f'Invalid format. Must be one of: {", ".join(valid_formats)}'
            }), 400
        
        # Get search results
        results = current_app.db_service.search_apis(
            query=query,
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