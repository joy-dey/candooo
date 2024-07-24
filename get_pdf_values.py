import datetime
from bson.json_util import dumps as bdumps
from bson import ObjectId
from build_config import CONFIG
import io
from util.conn_util import MongoMixin
from util.time_util import timeNow

account = MongoMixin.userDb[
    CONFIG['database'][0]['table'][0]['name']
]

profile = MongoMixin.userDb[
    CONFIG['database'][0]['table'][2]['name']
]

uploadFileDetails = MongoMixin.userDb[
    CONFIG['database'][0]['table'][16]['name']
]

loanApplication = MongoMixin.userDb[
    CONFIG['database'][0]['table'][13]['name']
]

state = MongoMixin.userDb[
    CONFIG['database'][0]['table'][6]['name']
]

block = MongoMixin.userDb[
    CONFIG['database'][0]['table'][15]['name']
]

district = MongoMixin.userDb[
    CONFIG['database'][0]['table'][14]['name']
]

auditInfo = MongoMixin.userDb[
    CONFIG['database'][0]['table'][19]['name']
]

loanStatusLog = MongoMixin.userDb[
    CONFIG['database'][0]['table'][18]['name']
]




async def getTotalApplications(**kwargs):
    district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    cursor = loanApplication.aggregate(
        [
            {
                '$match': {
                    'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                    'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                }
            },
            {
                '$count': 'totalLoanApplications'
            }
        ]
    )
    async for doc in cursor:
        return doc['totalLoanApplications']

    
async def loanSanctionedF(**kwargs):
    district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = loanApplication.aggregate(
        [
            {
                '$match': {
                    'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                    'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                }
            },
            {
                '$group': {
                    '_id': '$data.currentStatus',
                    'totalApplications': {'$sum': 1},
                    'totalSanctionedAmount': {'$sum': '$data.totalSanctionedAmountByBank'}
                }
            },
            {
                '$addFields': {
                    'status': '$_id'
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'status': 1,
                    'totalApplications': 1,
                    'totalSanctionedAmount': 1,
                }
            }
        ]
    )
    async for doc in dataQ:
        return doc
    

async def edpPendingF(**kwargs):
    district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    block = kwargs['block'] if 'block' in kwargs else None

    dataQ = loanApplication.aggregate(
        [
            {
                '$match': {
                    'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                    'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                    'data.talukblock': block if block else { '$exists': True },
                }
            },
            {
                '$addFields': {
                    'edpPending': {
                        '$cond': {
                            'if': {
                                '$and': [
                                    {'$in': ['$data.currentStatus', ['Loan Sanctioned', 'Disbursed']]},
                                    {'$ne': [{'$type': '$data.certificateIssueDate'}, 'long']}
                                ]
                            },
                            'then': 1,
                            'else': 0
                        }
                    },
                    'edpCompleted': {
                        '$cond': {
                            'if': {'$eq': [{'$type': '$data.certificateIssueDate'}, 'long']},
                            'then': 1,
                            'else': 0
                        }
                    }
                }
            },
            {
                '$group': {
                    '_id': None,
                    'edpPending': {'$sum': '$edpPending'},
                    'edpCompleted': {'$sum': '$edpCompleted'}
                }
            }
        ]
    )

    async for doc in dataQ:
        return doc

async def completedHomestayF(**kwargs):
    district = district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = auditInfo.aggregate(
        [
            {
                '$lookup': {
                    'from': 'loanApplication',
                    'localField': 'loanId',
                    'foreignField': '_id',
                    'as': 'loanAppInfo'
                }
            },
            {
                '$match': {
                    'constructionStatus': 'Incomplete',
                    'loanAppInfo.data.onlineSubmissionDate': {
                        '$exists': True
                    }
                }
            },
            {
                '$unwind': '$loanAppInfo'
            },
            {
                '$match': {
                    'loanAppInfo.data.onlineSubmissionDate': (
                        {'$gte': sYear, '$lte': eYear} if year else {'$exists': True}
                    ),
                    'loanAppInfo.data.unitDistrict': {'$in': district} if district else { '$exists': True },
                }
            },
            {
                '$count': 'completedHomestay'
            }
        ]   
    )

    async for doc in dataQ:
        return doc

async def defaultersF(**kwargs):
    district = district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = loanApplication.aggregate(
        [
                {
                    '$match': {
                        'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                        'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                        'isDefaulter': True
                    }
                },
                {
                    '$count': 'defaulters'
                },
                {
                    '$project': {
                        '_id': 0,
                        'defaulters': 1
                    }
                }
            ]
    )
    async for doc in dataQ:
        return doc



async def disbursedF(**kwargs):
    district = district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = loanStatusLog.aggregate(
        [
            {
                '$lookup': {
                    'from': 'loanApplication', 
                    'localField': 'loanApplicationId', 
                    'foreignField': '_id', 
                    'as': 'loanAppInfo'
                }
            },
            {
                
                '$match': {
                    'loanAppInfo.data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {
                        '$exists': True},
                    'loanAppInfo.data.unitDistrict': {'$in': district} if district else { '$exists': True },
                }
                
            },
              {
                '$unwind': '$disbursed'
            }, {
                '$unwind': '$disbursed.disbursedInfo'
            }, {
                '$group': {
                    '_id': None, 
                    'totalDisbursedApplications': {
                        '$sum': 1
                    }, 
                    'totalDisbursedAmount': {
                        '$sum': '$disbursed.disbursedInfo.amount'
                    }
                }
            }
        ]
    )

    async for doc in dataQ:
        return doc
    
async def districtWiseApplicationF(**kwargs):
    district = district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = loanApplication.aggregate(
        [
            {
                '$match': {
                    'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                    'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                }
            },
            {
                '$group': {
                    '_id': '$data.unitDistrict', 
                    'totalApplications': {'$sum': 1}
                }
            },
            {
                '$lookup': {
                    'from': 'district', 
                    'localField': '_id', 
                    'foreignField': '_id', 
                    'as': 'districtDetails', 
                    'pipeline': [
                        {'$project': {'_id': 0, 'districtName': 1}}
                    ]
                }
            },
            {
                '$unwind': '$districtDetails'
            },
            {
                '$addFields': {
                    'districtName': '$districtDetails.districtName'
                }
            },
            {
                '$project': {
                    '_id': 0, 
                    'totalApplications': 1, 
                    'districtName': 1
                }
            },
            {
                '$sort': {'_id': 1}
            }
        ]
    )
    districtWiseApplication = []
    async for doc in dataQ:
        districtWiseApplication.append(doc)
    if not districtWiseApplication:
        districtWiseApplication = [{'totalApplications': 0, 'districtName': 'None'}]
    return districtWiseApplication

async def districtWiseRejectedApplicationF(**kwargs):
    district = district = kwargs['district'] if 'district' in kwargs else None
    year = kwargs['year'] if 'year' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = loanApplication.aggregate(
        [
            {
                '$match': {
                    'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                    'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                }
            },
            {
                '$facet': {
                    'byBank': [
                        {
                            '$match': {
                                'data.currentStatus': 'Rejected/Returned',
                            }
                        },
                        {
                            '$match': {
                                'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True}
                            }
                        },
                        {
                            '$match': {
                                'data.rejectedByBank': True
                            }
                        },
                        {
                            '$group': {
                                '_id': '$data.unitDistrict',
                                'totalApplicationsBank': {
                                    '$sum': 1
                                }
                            }
                        },
                        {
                            '$lookup': {
                                'from': 'district', 
                                'localField': '_id',
                                'foreignField': '_id',
                                'as': 'districtDetails',
                                'pipeline': [
                                    {
                                        '$project': {
                                            '_id': 0,
                                            'districtName': 1
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            '$addFields': {
                                'districtName': {
                                    '$arrayElemAt': ['$districtDetails.districtName', 0]
                                }
                            }
                        },
                        {
                            '$project': {
                                'totalApplicationsBank': 1,
                                'districtName': 1
                            }
                        }
                    ],
                    'byDIC': [
                        {
                            '$match': {
                                'data.currentStatus': 'Rejected/Returned',
                            }
                        },
                        {
                            '$match': {
                                'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else { '$exists': True }
                            }
                        },
                        {
                            '$match': {
                                'data.rejectedByBank': False
                            }
                        },
                        {
                            '$group': {
                                '_id': '$data.unitDistrict',
                                'totalApplicationsDIC': {
                                    '$sum': 1
                                }
                            }
                        },
                        {
                            '$lookup': {
                                'from': 'district', 
                                'localField': '_id',
                                'foreignField': '_id',
                                'as': 'districtDetails',
                                'pipeline': [
                                    {
                                        '$project': {
                                            '_id': 0,
                                            'districtName': 1
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            '$addFields': {
                                'districtName': {
                                    '$arrayElemAt': ['$districtDetails.districtName', 0]
                                }
                            }
                        },
                        {
                            '$project': {
                                'totalApplicationsDIC': 1,
                                'districtName': 1
                            }
                        }
                    ]
                }
            },
            {
                '$project': {
                    'combined': {
                        '$concatArrays': ['$byBank', '$byDIC']
                    }
                }
            },
            {
                '$unwind': '$combined'
            },
            {
                '$group': {
                    '_id': '$combined._id',
                    'totalApplications': {
                        '$push': {
                            '$cond': {
                                'if': { '$gt': ['$combined.totalApplicationsBank', None] },
                                'then': '$combined.totalApplicationsBank',
                                'else': '$combined.totalApplicationsDIC'
                            }
                        }
                    },
                    'districtName': { '$first': '$combined.districtName' }
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'totalApplications': 1,
                    'districtName': 1
                }
            },
            {
                '$sort': {
                    '_id': 1
                }
            }
        ]
    )

    districtWizeRejectedApplication = []
    async for doc in dataQ:
        districtWizeRejectedApplication.append(doc)
    if not districtWizeRejectedApplication:
        districtWizeRejectedApplication = [{'totalApplications': 0, 'districtName': 'None'}]
    return districtWizeRejectedApplication



async def rejectionWiseApplication(**kwargs):
    year = kwargs['year'] if 'year' in kwargs else None
    district = kwargs['district'] if 'district' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    dataQ = loanStatusLog.aggregate(
        [
                {
                    '$facet': {
                        
                        'rejectedByBank': [
                            {
                            '$lookup': {
                                'from': 'loanApplication',
                                'localField': 'loanApplicationId',
                                'foreignField': '_id',
                                'as': 'loanAppInfo',
                                'pipeline': [
                                    {
                                        '$match': {
                                            'data.currentStatus': 'Rejected/Returned',
                                            'data.rejectedByBank': True ,
                                            'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                                            'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True}
                                        }
                                    },
                                    {
                                        '$project': {
                                            '_id': 1
                                        }
                                    }
                                ]
                            }
                        },
                        {
                            '$addFields': {
                                'loanAppInfoSize': {
                                    '$size': '$loanAppInfo'
                                }
                            }
                        },
                        {
                            '$match': {
                                'loanAppInfoSize': {
                                    '$gt': 0
                                }
                            }
                        },
                        {
                            '$group': {
                                '_id': None,
                                'reasons': {
                                    '$push': {
                                        '$last': '$rejected.reason'
                                    }
                                }
                            }
                        },
                        {
                            '$unwind': '$reasons'
                        },
                        {
                            '$unwind': '$reasons'
                        },
                            {
                                '$group': {
                                    '_id': '$reasons',
                                    'totalApplications': { '$sum': 1 }
                                }
                            },
                            {
                                '$project': {
                                    '_id': 1,
                                    'totalApplications': 1
                                }
                            },
                            {
                            '$sort': {
                                'totalApplications': -1
                            },
                        },
                        { '$limit': 10 },
                        ],
                        'rejectedByDIC': [
                            {
                                '$lookup': {
                                    'from': 'loanApplication',
                                    'localField': 'loanApplicationId',
                                    'foreignField': '_id',
                                    'as': 'loanAppInfo',
                                    'pipeline': [
                                        {
                                            '$match': {
                                                'data.currentStatus': 'Rejected/Returned',
                                                'data.rejectedByBank': False,
                                                'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                                                'data.onlineSubmissionDate': {'$gte': sYear,'$lte': eYear} if year else {'$exists': True}
                                            }
                                        },
                                        {
                                            '$project': {
                                                '_id': 1
                                            }
                                        }
                                    ]
                                }
                            },
                            {
                                '$addFields': {
                                    'loanAppInfoSize': {
                                        '$size': '$loanAppInfo'
                                    }
                                }
                            },
                            {
                                '$match': {
                                    'loanAppInfoSize': {
                                        '$gt': 0
                                    }
                                }
                            },
                            {
                                '$group': {
                                    '_id': None,
                                    'reasons': {
                                        '$push': {
                                            '$last': '$rejected.reason'
                                        }
                                    }
                                }
                            },
                            {
                                '$unwind': '$reasons'
                            },
                            {
                                '$unwind': '$reasons'
                            },
                            {
                                '$group': {
                                    '_id': '$reasons',
                                    'totalApplications': { '$sum': 1 }
                                }
                            },
                            {
                                '$project': {
                                    '_id': 1,
                                    'totalApplications': 1
                                }
                            },
                            {
                                '$sort': {
                                    'totalApplications': -1
                                }
                            },
                            { '$limit': 10 },
                        ]
                    }
                },
            ]
    )

    districtWizeRejectedApplication = []    
    async for doc in dataQ:
        districtWizeRejectedApplication.append(doc)
    if len(districtWizeRejectedApplication) == 0:
        districtWizeRejectedApplication = [{'totalApplications': 0, 'districtName': 'None'}]
    return districtWizeRejectedApplication


async def districtWiseSanctionedApplicationF(**kwargs):
    year = kwargs['year'] if 'year' in kwargs else None
    district = kwargs['district'] if 'district' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    pipeline = [
        {
            '$match': {
                'data.unitDistrict': {'$in': district} if district else { '$exists': True },
                'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True},
                'data.currentStatus': {
                '$nin': [
                    'Loan Sanctioned', 'Disbursed'
                ]
                }
            }
        },
        {
                '$group': {
                    '_id': '$data.unitDistrict', 
                    'totalApplications': {
                        '$sum': 1
                    }
                }
            }, {
                '$lookup': {
                    'from': 'district', 
                    'localField': '_id', 
                    'foreignField': '_id', 
                    'as': 'districtDetails'
                }
            }, {
                '$addFields': {
                    'districtName': '$districtDetails.districtName'
                }
            }, {
                '$unwind': '$districtName'
            }, {
                '$project': {
                    '_id': 0, 
                    'districtName': 1, 
                    'totalApplications': 1
                }
            }, {
                '$sort': {
                    'districtName': 1
                }
            }
        ]

    mFindRecord = loanApplication.aggregate(pipeline)
    result = []
    async for i in mFindRecord:
        result.append(i)
    return result


async def performanceWizeHomestays(**kwargs):
    year = kwargs['year'] if 'year' in kwargs else None
    district = kwargs['district'] if 'district' in kwargs else None
    sYear = kwargs['sYear'] if 'sYear' in kwargs else None
    eYear = kwargs['eYear'] if 'eYear' in kwargs else None
    pipeline = [
        {
            '$match': {
                'data.onlineSubmissionDate': {'$gte': sYear, '$lte': eYear} if year else {'$exists': True}
            }
        },
            {
                '$lookup': {
                    'from': 'auditInfo',
                    'localField': '_id',
                    'foreignField': 'loanId',
                    'as': 'auditInfo',
                    'pipeline': [
                        {
                            '$addFields': {
                                'stage1': '$auditData.stage1.stageStatus',
                                'stage2': '$auditData.stage2.stageStatus',
                                'stage3': '$auditData.stage3.stageStatus',
                                'stage4': '$auditData.stage4.stageStatus',
                                'stage5': '$auditData.stage5.stageStatus',
                                'stage6': '$auditData.stage6.stageStatus'
                            }
                        },
                        {
                            '$addFields': {
                                'stageOne': {
                                    '$cond': {
                                        'if': {
                                            '$eq': ['$stage1', 'complete']
                                        },
                                        'then': 1,
                                        'else': 0
                                    }
                                },
                                'stageTwo': {
                                    '$cond': {
                                        'if': {
                                            '$eq': ['$stage2', 'complete']
                                        },
                                        'then': 1,
                                        'else': 0
                                    }
                                },
                                'stageThree': {
                                    '$cond': {
                                        'if': {
                                            '$eq': ['$stage3', 'complete']
                                        },
                                        'then': 1,
                                        'else': 0
                                    }
                                },
                                'stageFour': {
                                    '$cond': {
                                        'if': {
                                            '$eq': ['$stage4', 'complete']
                                        },
                                        'then': 1,
                                        'else': 0
                                    }
                                },
                                'stageFive': {
                                    '$cond': {
                                        'if': {
                                            '$eq': ['$stage5', 'complete']
                                        },
                                        'then': 1,
                                        'else': 0
                                    }
                                },
                                'stageSix': {
                                    '$cond': {
                                        'if': {
                                            '$eq': ['$stage6', 'complete']
                                        },
                                        'then': 1,
                                        'else': 0
                                    }
                                }
                            }
                        },
                        {
                            '$project': {
                                '_id': {
                                    '$toString': '$_id'
                                },
                                'stageOne': 1,
                                'stageTwo': 1,
                                'stageThree': 1,
                                'stageFour': 1,
                                'stageFive': 1,
                                'stageSix': 1
                            }
                        }
                    ]
                }
            },
            {
                '$unwind': '$auditInfo'
            },
            {
                '$lookup': {
                    'from': 'loanStatusLog',
                    'localField': '_id',
                    'foreignField': 'loanApplicationId',
                    'as': 'disbursementInfo',
                    'pipeline': [
                        {
                            '$addFields': {
                                'disbursementDetails': {
                                    '$first': '$disbursed'
                                }
                            }
                        },
                        {
                            '$addFields': {
                                'disbursedDate': {
                                    '$first': '$disbursementDetails.disbursedInfo.date'
                                }
                            }
                        },
                        {
                            '$project': {
                                '_id': {
                                    '$toString': '$_id'
                                },
                                'disbursedDate': 1
                            }
                        }
                    ]
                }
            },
            {
                '$unwind': '$disbursementInfo'
            },
            {
                '$project': {
                    '_id': {
                        '$toString': '$_id'
                    },
                    'auditInfo': 1,
                    'disbursementInfo': 1

                }
            }
        ]
    if district:
        pipeline.insert(0, {
            '$match': {
                'data.unitDistrict': {
                    '$in': district
                }
            }
        })
            
    xCurrentDate = datetime.datetime.fromtimestamp(timeNow() / 1000 / 1000)
    xCurrentDate = xCurrentDate.strftime('%Y-%m-%d')
    xCurrentDate = datetime.datetime.strptime(xCurrentDate, '%Y-%m-%d')

    xGreenStage = 0
    xYellowStage = 0
    xRedStage = 0

        
    mFindApplication = loanApplication.aggregate(pipeline)
    async for i in mFindApplication:
        if i.get('auditInfo') and i.get('disbursementInfo').get('disbursedDate'):
            xTotalStages = i.get('auditInfo').get('stageOne') + i.get('auditInfo').get('stageTwo') + i.get('auditInfo').get('stageThree') + i.get('auditInfo').get('stageFour') + i.get('auditInfo').get('stageFive') + i.get('auditInfo').get('stageSix')
            
            xDisbursedDate = datetime.datetime.fromtimestamp(i.get('disbursementInfo').get('disbursedDate') / 1000 / 1000)
            xDisbursedDate = xDisbursedDate.strftime('%Y-%m-%d')
            xDisbursedDate = datetime.datetime.strptime(xDisbursedDate, '%Y-%m-%d')
            year_diff = xCurrentDate.year - xDisbursedDate.year
            month_diff = xCurrentDate.month - xDisbursedDate.month

            if xCurrentDate.day < xDisbursedDate.day:
                month_diff -= 1
            xMonthDifference = year_diff * 12 + month_diff
            if xTotalStages:
                if xMonthDifference <= xTotalStages * 2:
                    xGreenStage += 1
                elif xMonthDifference > xTotalStages * 2 and xMonthDifference <= xTotalStages * 2 + 2:
                    if xTotalStages == 6:
                        xGreenStage += 1
                    else:
                        xYellowStage += 1
                elif xMonthDifference > xTotalStages * 2 + 2:
                    if xTotalStages == 6:
                        xGreenStage += 1
                    else:
                        xRedStage += 1
        
    result = [
        {
            'Green': xGreenStage,
            'Yellow': xYellowStage,
            'Red': xRedStage
        }
    ]

    return result